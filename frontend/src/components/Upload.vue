<script setup>
import { ref, reactive } from 'vue';
import { call_api, upload_files, get_image } from "../assets/API.js";

/** Vue model that contains reactive object with at least two following fields:
 * * albums - reactive component with list of albums,
 *            where album is represented as the object with at least two following fields:
 *     * id - id of the album
 *     * name - name of the album
 * * show - true if Upload form should be shown, false otherwise.
 */
const model = defineModel();

/** Error message to be displayed. Not displayed when null. */
const error_message = ref(null);
/** Success message to be displayed. Not displayed when null. */
const success_message = ref(null);
/** How many photos are currently in the uploading process. When 0, the loading animation is hidden */
const loading = ref(0);

/** Reactive list of the uploaded images in the form, where each image is represented as
 * a dictionary with the following fields:
 * * id is an integer identificator of the uploded image
 * * caption is a string description of the image
 * * album is an integer album id where photo is stored
 * * date is the date of uploading
 */
var images = reactive([]);

/** Hides the current Upload dialog, resets required fields, reloads page if any image was uploaded. */
function hide() {
  model.value.show = false;
  error_message.value = null;
  success_message.value = null;
  if (images.length>0) {
    window.location.reload();
  }
}

/**
 * Uploads the photo to the API and shows it in the form. Zip files are also
 * supported.
 * @param file Image File that user wants to upload
 */
async function upload(files) {
  loading.value++;
  try {
    let response_data = await upload_files(files);
    error_message.value = null;
    for (let image of response_data) {
      image["src"] = await get_image(image["id"]);
      images.push(image);
    }
  } catch (error) {
    error_message.value = error;
  }
  loading.value--;
}

/**
 * Handles photo uploading to the input element. Uploaded photos are sent to the API
 * and shown in the form.
 * @param event Event of photo uploading to the input element.
 */
function handle_upload(event) {
  const selectedFiles = Array.from(event.target.files);
  if(!selectedFiles) return;
  upload([...selectedFiles]);
}

/**
 * Handles the event of image file drag-and-drop. Dragged photos are sent to the API
 * and shown in the form.
 * @param event Event of dropping the images to the designated place.
 */
function drop(event) {
  let droppedFiles = event.dataTransfer.files;
  if(!droppedFiles) return;
  upload([...droppedFiles]);
}

/**
 * Deletes the photo among the uploaded photos.
 * @param local_id The position of photo that needs to be deleted in "images" list
 */
async function delete_photo(local_id) {
  try {
    await call_api("DELETE", "photo", {id: images[local_id]["id"]});
    error_message.value = null;
    images.splice(local_id, 1);
  } catch (error) {
    error_message.value = error;
  }
}

/**
 * Saves the applied changes (captions) to the albums in the form.
 */
async function save() {
  console.log("save is called");
  error_message.value = null;
  for (let image of images) {
    const id = image["id"];
    const new_caption = document.getElementById(id+"_caption").value;
    const new_album_id = document.getElementById(id+"_album").value;
    if (image["caption"]!=new_caption || image["album"]!=new_album_id) {
      try {
        await call_api("UPDATE", "photo", {id: id, caption: new_caption, album: new_album_id});
        image["caption"] = new_caption;
        image["album"] = new_album_id;
      } catch (error) {
        error_message.value = error;
      }
    }
  }
  // if not a single error appeared, show success message
  if (error_message.value==null) {
    success_message.value = "All images were successfully updated."
    await new Promise(r => setTimeout(r, 700));
    hide();
  }
}

</script>

<style>
#drop-zone {
  border: 2px dashed #aaa;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  width: 100%;
}
#drop-zone:hover {
  border-color: #666;
}
#file-input {
  display: none;
}

.uploaded_images_table {
  width: 100%;
  overflow: hidden;
  margin-top: 30px;
  border-collapse: separate; 
  border-spacing: 15px;
}
.modal-dialog {
  min-width: 40%;
}
.uploaded_image_row {
  height: 80px;
}
.uploaded_image {
  width: 20%;
}
.uploaded_image > img {
  max-width: 100%;
  max-height: 100%;
  border-radius: 10px;
  margin: auto;
}
.uploaded_caption {
  width: 55%;
  position: relative;
}
.uploaded_caption > textarea {
  margin: 10px;
  width: calc( 100%  - 20px);
  height: calc( 100%  - 20px);
  resize: none;
  border-radius: 7px;
  padding-left: 10px;
  padding-right: 10px;
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  left: 0;
  overflow-y: scroll;
  border: solid #888 1px;
}
</style>

<template>
  <div :hidden="!model.show" class="modal black_cover" tabindex="-1" @click="hide">
      <div class="modal-dialog" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Upload image</h5>
            <button type="button" @click="hide" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="alert alert-danger" role="alert" :hidden="error_message==null">
              <small>{{ error_message }}</small>
          </div>
          <div class="alert alert-success" role="alert" :hidden="success_message==null">
              <small>{{ success_message }}</small>
          </div>
          <div class="modal-body">
            <label id="drop-zone" @drop.prevent="drop" @dragover.prevent>
              <svg xmlns="http://www.w3.org/2000/svg" height="64px" viewBox="0 -960 960 960" width="64px" fill="#333">
                <path d="M260-160q-91 0-155.5-63T40-377q0-78 47-139t123-78q25-92 100-149t170-57q117 0 198.5 81.5T760-520q69 8 114.5 59.5T920-340q0 75-52.5 127.5T740-160H520q-33 0-56.5-23.5T440-240v-206l-64 62-56-56 160-160 160 160-56 56-64-62v206h220q42 0 71-29t29-71q0-42-29-71t-71-29h-60v-80q0-83-58.5-141.5T480-720q-83 0-141.5 58.5T280-520h-20q-58 0-99 41t-41 99q0 58 41 99t99 41h100v80H260Zm220-280Z"/>
              </svg>
              <h5>Drop images here, or click to upload.</h5>
              <input type="file" id="file-input" multiple accept="image/png, image/jpg, image/jpeg, image/webp, image/gif, application/zip" @change="handle_upload" />
            </label>
            <table class="uploaded_images_table">
              <tbody>
                <tr v-for="(image, i) in images" class="uploaded_image_row" :key="image['id']">
                  <td class="uploaded_image"><img :src="image['src']"></td>
                  <td class="uploaded_caption"><textarea :id="image['id'] + '_caption'" placeholder="Write caption to your uploaded image here...">{{ image['caption'] }}</textarea></td>
                  <td class="uploaded_album">
                    <select name="album" class="form-select" :id="image['id'] + '_album'">
                      <option v-for="album in model.albums" :value="album['id']" :selected="image['album']==album['id']">
                        {{ album['name']!='' ? album['name'] : "Unclassified" }}
                      </option>
                    </select>
                  </td>
                  <td class="uploaded_delete">
                    <a>
                    <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e40000" @click="delete_photo(i)">
                      <path d="m336-280 144-144 144 144 56-56-144-144 144-144-56-56-144 144-144-144-56 56 144 144-144 144 56 56ZM480-80q-83 0-156-31.5T197-197q-54-54-85.5-127T80-480q0-83 31.5-156T197-763q54-54 127-85.5T480-880q83 0 156 31.5T763-763q54 54 85.5 127T880-480q0 83-31.5 156T763-197q-54 54-127 85.5T480-80Zm0-80q134 0 227-93t93-227q0-134-93-227t-227-93q-134 0-227 93t-93 227q0 134 93 227t227 93Zm0-320Z"/>
                    </svg>
                    </a>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="loading_dots" id="loader" :hidden="loading==0"></div>
            <button style="float: right;" class="btn btn-primary mt-4" @click="save" :hidden="images.length==0">
              Save changes
            </button>
          </div>
        </div>
      </div>
    </div>

</template>