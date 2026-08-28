#!/usr/bin/env python3
import torch
import argparse
from train import ImageToTextModel

from transformers import GPT2TokenizerFast
from tokenizers import Tokenizer
from PIL import Image
from tokenizers.processors import TemplateProcessing
import open_clip

class ImageToTextPredict():
    """Class responsible for predicting the caption of the passed image and detect
    the most appropriate album name that would math the passed image.
    """
    def __init__(self, model_path = "model.pt", album_matching_threshold = 0.2, prediction_batch_size = 32):
        """Initializes the ImageToTextPredict class. Loads the required models,
        tokenizers for them, and sets the threshold for album matching.
        :param str model_path: The path to the image captioning model of ImageToTextModel class.
        :param float album_matching_threshold: The minimum cosine similarity that should
        be satisfied between image embedding and album name embedding to classify the image.
        If all cosine similarities are below the threshold, the image will not be classified
        to match any album.
        """
        self._album_matching_threshold = album_matching_threshold
        self._prediction_batch_size = prediction_batch_size

        # Detect device
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")
        
        # Loading the models
        self._model = torch.load(model_path, weights_only=False, map_location=torch.device(self.device.type))
        self._clip_model, _, self.preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        self._clip_model = self._clip_model.to(self.device)

        # Loading tokenizer for self._model
        tokenizer = Tokenizer.from_pretrained("openai-community/gpt2")
        tokenizer.post_processor = TemplateProcessing(
            single="$0 [EOS]",
            special_tokens=[
                ("[EOS]", tokenizer.token_to_id("<|endoftext|>"))
            ],
        )
        padding_id = tokenizer.encode("\x00").ids[0]
        tokenizer.enable_padding(
            direction="right",
            pad_id=padding_id,
            pad_type_id=padding_id,
            pad_token=tokenizer.id_to_token(padding_id)
        )
        self._tokenizer = GPT2TokenizerFast(tokenizer_object=tokenizer)

        # Loading tokenizer for the CLIP model
        self._clip_tokenizer = open_clip.get_tokenizer('ViT-B-32')

    @torch.no_grad()
    def predict(self, image_paths: list[str], albums: list[str]) -> list[tuple[str, int]]:
        """Generates captions for the given images and classifies them among provided albums.
        Returns a list of tuples of text descriptions and indecies of the albums from the provided album list
        "albums" that is the most suitable for the provided image. If no album name matches
        image close enough (does not surpass album matching threshold), index -1 will be returned,
        same will happen if empty list of albums was provided.
        :param str image_path: List of paths to the images for which caption should be generated and
        which should be classified among albums. The path should be relative with respect to
        the current working directory.
        :param list[str] albums: List of album names among which the image must be classified.
        :return: Tuple where first member is a generated text caption for the provided image,
        and second member is an index of the album that is the most suitable for the provided
        image, -1 is returned as index if no album is suitable enough (i.e. none of the
        provided albums surpasses the album_matching_threshold set during the initialization of this class).
        :rtype: tuple[str, int]
        """
        images = []
        for image_path in image_paths:
            image = Image.open(image_path)
            image = self.preprocess(image).to(self.device)
            images.append(image)
        images_dataset = torch.utils.data.StackDataset(images)
        images_dataloader = torch.utils.data.DataLoader(images_dataset, self._prediction_batch_size)
            
        self._model.eval()
        self._clip_model.eval()

        texts = []
        # Generating text from predicted embeddings
        for (image_batch, ) in images_dataloader:
            preds = self._model.predict(image_batch)
            texts.extend(self._tokenizer.batch_decode(preds, True))

        # Comparing albums to image embedding
        if len(albums)==0:
            return list(map(lambda x: (x,), texts))
        album_tokens = self._clip_tokenizer(albums).to(self.device)
        predictions = []
        with torch.no_grad(), torch.autocast(self.device.type):
            album_features = self._clip_model.encode_text(album_tokens)
            album_features /= album_features.norm(dim=-1, keepdim=True)
        j = 0
        for (image_batch, ) in images_dataloader:
            with torch.no_grad(), torch.autocast(self.device.type):
                image_features = self._clip_model.encode_image(image_batch)
                image_features /= image_features.norm(dim=-1, keepdim=True)

            text_probs = (image_features @ album_features.T).max(1)
            for i in range(image_batch.shape[0]):
                if text_probs.values[i].item()>self._album_matching_threshold:
                    best_album_index = text_probs.indices[i].item()
                else:
                    best_album_index = -1
                predictions.append((texts[j], best_album_index))
                j+=1
        
        return predictions

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", default="model.pt", type=str, help="Path to the trained model to generate caption. It must be an instance of the ImageToTextModel class.")
    parser.add_argument("--album_matching_threshold", default=0.15, type=float, help="The threshold of the maximum cosine distance to classify image to the album. Exceeding the provided distance for all of the albums will leave the image unclassified among the albums.")
    parser.add_argument("image_path", type=str, help="A path to the image for which caption should be generated and which should be classified among the provided albums.")
    parser.add_argument("albums", nargs=argparse.REMAINDER, help="Album names among which the provided image should be classified with respect to album matching threshold.")
    
    args = parser.parse_args()

    im = ImageToTextPredict()
    caption, album_id = im.predict([args.image_path], args.albums)[0]
    print(f"Caption generated for the image: {caption}\n")
    if album_id is None:
        print("No album matches image.")
    else:
        print(f'Album "{args.albums[album_id]}" is the best match for the provided image.')
