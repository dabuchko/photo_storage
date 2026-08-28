#!/usr/bin/env python3
import os
import argparse
import datetime
import re

from tqdm import tqdm

import torch
import torchvision.transforms.v2 as v2

from transformers import GPT2LMHeadModel, GPT2TokenizerFast, AutoTokenizer
from tokenizers import Tokenizer
from tokenizers.processors import TemplateProcessing
from datasets import load_dataset
import open_clip
from transformers import GenerationConfig, LogitsProcessor

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", default=32, type=int, help="Batch size.")
parser.add_argument("--epochs", default=50, type=int, help="Number of epochs.")
parser.add_argument("--seed", default=42, type=int, help="Random seed.")
parser.add_argument("--threads", default=1024, type=int, help="Maximum number of threads to use.")
parser.add_argument("--hidden", default=1024, type=int, help="The size of the hidden layer that converts CLIP embedding to GPT2 embedding.")
parser.add_argument("--learning_rate", default=0.0001, type=float, help="Learning rate for the optimizer.")
parser.add_argument("--token_weight_norm", default=0.8, type=float, help="Power to which token weights will be raised. Power 1.0 stands for normalization 1/(frequency in train data).")

class ImageToTextModel(torch.nn.Module):
    """Image captioning model that accepts images as input and produces text descriptions
    of the given images as output.
    """
    def __init__(self, encoder_size: int, hidden_size: int, encoder: torch.nn.Module,
                 pad_token_id: int = 0, eos_token_id: int = 0, prefix_length: int = 10
                 ) -> None:
        """Initializes the image captioning model.

        :param int encoder_size: The size of the vector produced by the encoder module.
        :param int hidden_size: The size of hidden layer that converts encoder embeddings to GPT2 embeddings.
        :param torch.nn.Module encoder: The encoder model encoding image into latent space vector of size "encoder_size".
        The encoder must produce a tensor of size [BATCH_SIZE, encoder_size].
        :param int eos_token_id: The id of th end of sequence token. (default 0)
        :param int prefix_length: The size of the prefix that will be generated from image embedding and passed to GPT2 model.
        """
        super().__init__()
        self._prefix_length = prefix_length
        self._pad_token_id = pad_token_id
        self._eos_token_id = eos_token_id

        self.encoder = encoder.requires_grad_(False)
        self.encoder.eval()
        self.decoder = GPT2LMHeadModel.from_pretrained("openai-community/gpt2", eos_token_id=eos_token_id)
        self.decoder = self.decoder.requires_grad_(False)
        self.decoder.eval()
        
        self.linear1 = torch.nn.Linear(encoder_size, hidden_size)
        self.linear2 = torch.nn.Linear(hidden_size, self.decoder.config.n_embd * self._prefix_length)

    def forward(self, images: torch.Tensor, captions: torch.Tensor) -> torch.Tensor:
        """Forward pass. Should be used only when target captions are available.
        For the inference without target captions, the "predict" function must be used.
        :param torch.Tensor images: A batch of images as they are accepted by the encoder.
        :param torch.Tensor captions: A batch of tokenized captions as they are accepted by
        transformers.GPT2LMHeadModel input_ids argument. Right padding is expected.
        The size of passed tensor must be [BATCH_SIZE, MAX_LENGTH, TOTAL_NUM_OF_TOKENS],
        where MAX_LENGTH is the maximum length among the encoded captions (in tokens),
        and TOTAL_NUM_OF_TOKENS is the vocab_size from GPT2Config (50257).
        """
        images = self.encoder.encode_image(images)
        
        x = torch.relu(self.linear1(images))
        x = self.linear2(x)
        x = x.reshape(x.shape[0], self._prefix_length, -1)
        
        captions_embeds = self.decoder.transformer.wte(captions)
        inputs_embeds = torch.cat([x, captions_embeds], 1)

        logits = self.decoder(inputs_embeds=inputs_embeds).logits[:, self._prefix_length - 1:]
        return logits
    
    class EndOfTextProcessor(LogitsProcessor):
        """Processes the logits produced by transformers.PretrainedModel and
        any of its children, encoraging the sooner appearance of the end of
        sequence tokens. This is done simply by adding the length of
        currently generated sequence directly to logits of the end of sequence token.
        """
        def __init__(self, eos_token_id: int):
            self._eos_token_id = eos_token_id
        
        def __call__(self, input_ids, scores):
            scores[:, self._eos_token_id] += torch.tensor(input_ids.shape[-1])
            return scores

    @torch.no_grad
    def predict(self, images: torch.Tensor, max_length: int = 512) -> torch.Tensor:
        """Generates the caption for the provided images.
        Does not use gradient. For training purposes the forward function should be used.
        :param torch.Tensor images: Images to be captioned in a shape as the encoder expects.
        :param int max_length: Maximum length of the generated captions. If any of the
        captions did not produce the end of sequence token until this moment, the
        generation will stop in any case without adding the end of sequence token
        to the end of the unfinished captions. (default 512)
        """
        images = self.encoder.encode_image(images)
        
        x = torch.relu(self.linear1(images))
        x = self.linear2(x)
        x = x.reshape(x.shape[0], self._prefix_length, -1)

        gen_config = GenerationConfig(
            max_length=self._prefix_length + max_length,
            do_sample=False,
            num_beams=1
        )
        self.decoder.config.output_attentions = False
        self.decoder.config.pad_token_id = self._pad_token_id

        logits_processor = self.EndOfTextProcessor(self._eos_token_id)
        res = self.decoder.generate(inputs_embeds=x, generation_config=gen_config,
                                    pad_token_id=self._pad_token_id,
                                    logits_processor=[logits_processor],
                                    repetition_penalty=1.1)
        return res


class COCOCollate:
    """Class that provides an appropriate collate function for COCO dataset
       for the Dataloader class from PyTorch. Provides the function "collate",
       which preprocesses images with the provided function and tokenizes captions,
       preparing data in appropriate format for training.
    """
    def __init__(self, tokenizer: AutoTokenizer, image_preprocess = None):
        """Sets the tokenizer and image preprocessing function that should be
        used during collation.

        :param AutoTokenizer tokenizer: Tokenizer that will be used to tokenize captions.
        :param function image_preprocess: Function that should be applied to every image
        (default None - no function is applied).
        """
        self.tokenizer = tokenizer
        self.image_preprocess = image_preprocess
    
    def collate(self, batch: list) -> tuple[torch.Tensor, torch.Tensor]:
        """Collates the provided batch by utilizing the tokenizer and
        image preprocessing function from the current class.

        :param list batch: List of the COCO dataset items to be collated.
        :return: Tuple with first element being a batch of preprocessed images
        with size [BATCH_SIZE, ...] where "..." stands for the rest parameters
        produced by the provided image preprocessing function. The second element
        in the tuple is tokenized captions of size [BATCH_SIZE, MAX_LENGTH, NUMBER_OF_TOKENS],
        where MAX_LENGTH is the maximum length of the captions in tokens provided
        by the tokenizer and NUMBER_OF_TOKENS is the total number of tokens supported by the
        provided tokenizer.
        :rtype: tuple[torch.Tensor, torch.Tensor]
        """
        images = []
        captions = []
        for item in batch:
            if self.image_preprocess is not None:
                image = self.image_preprocess(item["image"])
            else:
                image = item["image"]
            images.append(image)
            captions.append(item["sentences"]["raw"])
        images = torch.stack(images, 0)
        captions = self.tokenizer(captions, padding="longest", return_tensors="pt", truncation=True, max_length=512)
        input_ids, attention_mask = captions["input_ids"], captions["attention_mask"].float()
        return images, input_ids

def main(args: argparse.Namespace) -> None:
    # Set the random seed and the number of threads.
    if args.seed is not None:
        torch.manual_seed(args.seed)

    if args.threads is not None and args.threads > 0:
        torch.set_num_threads(args.threads)
        torch.set_num_interop_threads(args.threads)
    
    # Create logdir name
    args.logdir = os.path.join("logs", "{}-{}-{}".format(
        os.path.basename(globals().get("__file__", "notebook")),
        datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        ",".join(("{}={}".format(re.sub("(.)[^_]*_?", r"\1", k), v) for k, v in sorted(vars(args).items())))
    ))

    # Detect device
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    # Load pretrained CLIP model
    clip_model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
    
    # Create tokenizer
    tokenizer = Tokenizer.from_pretrained("openai-community/gpt2")
    tokenizer.post_processor = TemplateProcessing(
        single="$0 [EOS]",
        special_tokens=[
            ("[EOS]", tokenizer.token_to_id("<|endoftext|>"))
        ],
    )
    padding_id = tokenizer.encode("\x00").ids[0]
    print(padding_id)
    tokenizer.enable_padding(
        direction="right",
        pad_id=padding_id,
        pad_type_id=padding_id,
        pad_token=tokenizer.id_to_token(padding_id)
    )
    tokenizer = GPT2TokenizerFast(tokenizer_object=tokenizer)
    eos_id = tokenizer.eos_token_id

    # Create a preprocessing pipeline.
    train_preprocessing = v2.Compose([
        v2.AutoAugment(),
        preprocess
    ])
    test_preprocessing = v2.Compose([
        preprocess
    ])

    # Load dataset
    dataset = load_dataset("HuggingFaceM4/COCO")

    # Define the dataloaders
    train_collate_obj = COCOCollate(train_preprocessing, tokenizer)
    test_collate_obj = COCOCollate(test_preprocessing, tokenizer)
    train_dataloader = torch.utils.data.DataLoader(dataset["train"], args.batch_size, shuffle=True, collate_fn=train_collate_obj.collate, num_workers=3, prefetch_factor=3)
    dev_dataloader = torch.utils.data.DataLoader(dataset["validation"], args.batch_size, collate_fn=test_collate_obj.collate, num_workers=3, prefetch_factor=3)
    test_dataloader = torch.utils.data.DataLoader(dataset["test"], args.batch_size, collate_fn=test_collate_obj.collate, num_workers=3, prefetch_factor=3)

    # Define the model
    model = ImageToTextModel(512, args.hidden, clip_model, padding_id, eos_id)
    model = model.to(device)

    # Compute weights of each token.
    weights = torch.ones((len(tokenizer),), device=device)
    pbar = tqdm(train_dataloader, desc="Computing token weights", unit="batch", dynamic_ncols=True, leave=False)
    for images, captions in pbar:
        images = images.to(device)
        captions = captions.to(device)
        for token in captions.tolist():
            weights[token] += 1
    weights = weights ** (-args.token_weight_norm)

    # Define the loss function, optimizer, and weight decay
    cse_loss = torch.nn.CrossEntropyLoss(weight=weights, ignore_index=padding_id)
    optimizer = torch.optim.AdamW(filter(lambda l: l.requires_grad, model.parameters()), lr=args.learning_rate)
    warmup = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda step: min((step + 1) / 3000, 1.0))

    for epoch in range(args.epochs):
        # Train the model
        model.train()
        train_loss = 0
        train_accuracy = 0
        description_prefix = "Epoch {}/{}".format(epoch + 1, args.epochs)
        pbar = tqdm(train_dataloader, desc=description_prefix, unit="batch", dynamic_ncols=True, leave=False)
        i = 0
        for images, captions in pbar:
            images = images.to(device)
            captions = captions.to(device)
            optimizer.zero_grad()
            outputs = model(images, captions[:, :-1])
            loss = cse_loss(outputs.permute(0, 2, 1), captions)
            loss.backward()
            optimizer.step()
            warmup.step()
            train_loss += loss.item()
            train_accuracy += (outputs.argmax(dim=-1)[captions!=padding_id] == captions[captions!=padding_id]).float().mean().item()
            i += 1
            pbar.set_description(f"{description_prefix} loss: {train_loss / i :.4f}, accuracy: {train_accuracy / i :.4f}")
        train_loss /= len(train_dataloader)
        train_accuracy /= len(train_dataloader)

        # Test the model on the development set
        model = model.eval()
        dev_loss = 0
        dev_accuracy = 0
        with torch.no_grad():
            for images, captions in dev_dataloader:
                images = images.to(device)
                captions = captions.to(device)
                outputs = model(images, captions[:, :-1])
                dev_loss += cse_loss(outputs.permute(0, 2, 1), captions)
                dev_accuracy += (outputs.argmax(dim=-1)[captions!=padding_id] == captions[captions!=padding_id]).float().mean().item()
        dev_loss /= len(dev_dataloader)
        dev_accuracy /= len(dev_dataloader)

        # Print the results
        print(f"Epoch {epoch+1}/{args.epochs}, Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.4f}, Dev Loss: {dev_loss:.4f}, Dev Accuracy: {dev_accuracy:.4f}")
    
        # Save the model
        os.makedirs(args.logdir, exist_ok=True)
        model_path = os.path.join(args.logdir, str(epoch)+"_model.pt")
        torch.save(model, model_path)

if __name__ == "__main__":
    args = parser.parse_args([] if "__file__" not in globals() else None)
    main(args)
