<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue';
import { call_api, get_image } from "../assets/API.js";

/** Vue model that must be a reactive dictionary with at least three following fields:
 * * images - is a list of images where every image is represented by a
 *            dictionary with at least four the following fields:
 *     * id - integer id of the photo
 *     * caption - string description of the photo
 *     * album - integer id of the album current photo belongs to
 *     * date - uploading date of the image
 *     * name - original name of the uploaded file
 * * show_local_id - is an integer containing a position of the image in images
 *                   list that needs to be displayed in ImageViewer. Null if no
 *                   image should be displayed.
 * * loading_fn - void function that requests more images to be loaded to the images list.
 */
const model = defineModel();
/** List of albums where each album is represented by a dictionary with album 'id' and album 'name'. */
const albums = reactive([]);

/** Error message to be displayed. Not displayed when null. */
const error_message = ref(null);
/** Boolean reference that is true when options menu is displayed. False when hidden. */
const show_options = ref(false);
/** Boolean reference that is true when album selection menu is displayed. False when hidden. */
const show_album_selection = ref(false);
/** Boolean reference on whether user currently changes caption and changing caption
 * form should be displayed. True to be displayed, false to be hidden.
 */
const changing_caption = ref(false);
/** Error message for the caption editing form. Not displayed when null. */
const caption_error_message = ref(null);
/** Success message for the caption editing form. Not displayed when null. */
const caption_success_message = ref(null);

/**
 * Returns the local path to currently displayed image. If the image is not
 * stored locally yet, then asynchronously loads the image and returns field
 * where the image will be stored after loading is done.
 */
function get_image_path() {
  if (model.value.images[model.value.show_local_id]["local_path"]==null) {
    get_image(model.value.images[model.value.show_local_id]["id"]).then(path => {
      model.value.images[model.value.show_local_id]["local_path"] = path;
    });
  }
  return model.value.images[model.value.show_local_id]['local_path'];
}

/** Hides ImageViewer, resets required properties for further usage. */
function cancel() {
  model.value.show_local_id = null;
  error_message.value = null;
}

/** Navigate to the previous photo. */
function left() {
  if (model.value.show_local_id!=0) {
    model.value.show_local_id--;
  }
  error_message.value = null;
}

/** Navigate to the next photo. */
function right() {
  if (model.value.show_local_id!=model.value.images.length-1) {
    model.value.show_local_id++;
    if (model.value.show_local_id==model.value.images.length-1) {
      model.value.loading_fn();
    }
  }
  error_message.value = null;
}

/**
 * Show options (when hidden) or hide (when shown).
 * @param event Click event to show options at the place of the click.
 */
async function show_hide_options(event) {
  show_options.value = !show_options.value;
  if (show_options.value) {
    var el = document.getElementById('options');
    el.style.top = (event.clientY - 5) + "px";
    await nextTick();
    el.style.left = (event.clientX + 5 - el.offsetWidth ) + "px";
  }
  error_message.value = null;
}

/** Hides options and resets the required values. */
function hide_options(event = null, force = false) {
  if (force || (
    !document.getElementById("options").matches(':hover') && (
      !show_album_selection.value || !document.getElementById("album_selection").matches(':hover')
    )
  )) {
    show_options.value = false;
    show_album_selection.value = false;
  }
  error_message.value = null;
}

/** Shows caption editing form. */
function change_caption() {
  changing_caption.value = true;
  caption_error_message.value = null;
  caption_success_message.value = null;
  hide_options();
}

/** Hides caption editing form. */
function stop_changing_caption() {
  changing_caption.value = false;
  caption_error_message.value = null;
  caption_success_message.value = null;
}

/** Submits caption editing form. */
async function submit_caption() {
  caption_error_message.value = null;
  caption_success_message.value = null;
  
  let new_caption = document.getElementById("new_caption").value;
  try {
    await call_api("UPDATE", "photo",
      {
        id: model.value.images[model.value.show_local_id]["id"],
        caption: new_caption,
        album: model.value.images[model.value.show_local_id]["album"]
    });
    model.value.images[model.value.show_local_id]["caption"] = new_caption;
    caption_success_message.value = "Caption was successfully updated";
    await new Promise(r => setTimeout(r, 700));
    stop_changing_caption();
  } catch (error) {
    caption_error_message.value = error;
  }
}

/** Opens menu to select album where the current image should be moved. */
async function move() {
  show_album_selection.value = true;
  var options_el = document.getElementById("options");
  var el = document.getElementById('album_selection');
  el.style.top = options_el.style.top;
  await nextTick();
  el.style.left = options_el.offsetLeft - el.clientWidth + "px";
  while (albums.length>0) albums.pop();
  (await call_api("GET", "albums", null)).forEach(el => {
    if (el["name"]=="") el["name"] = "Unclassified";
    albums.push(el)
  });
}

/**
 * Moves the current image to the specified album.
 * @param album_id Id of album where image should be moved to.
 */
async function move_to(album_id) {
  try {
    let old_album = model.value.images[model.value.show_local_id]["album"];
    await call_api("UPDATE", "photo", {
        id: model.value.images[model.value.show_local_id]["id"],
        caption: model.value.images[model.value.show_local_id]["caption"],
        album: album_id
    });
    error_message.value = null;
    if (window.location.hash.slice(1)==old_album && old_album!=album_id) {
      model.value.images.splice(model.value.show_local_id, 1);
      // switch to the other image if any
      if (model.value.show_local_id>0) left();
      else if (model.value.images.length==0) cancel();
    }
  } catch (error) {
      error_message.value = error;
  }
  hide_options(null, true);
}

/** Downloads currently displayed image by ImageViewer. */
function download_image() {
  hide_options(null, true);
  var a = document.createElement('a');
  a.href = model.value.images[model.value.show_local_id]["local_path"];
  a.download = model.value.images[model.value.show_local_id]["name"];
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  error_message.value = null;
}

/** Downloads metadata of the currently displayed image by ImageViewer. */
async function download_metadata() {
  try {
    let response_data = await call_api("POST",
            "photo", {ids: [model.value.images[model.value.show_local_id]["id"]]});
    error_message.value = null;
    let data_download_link = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(response_data));
    var a = document.createElement('a');
    a.href = data_download_link;
    a.download = "metadata.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (error) {
    error_message.value = error;
  }
  hide_options(null, true);
}

/** Deletes currently displayed photo. */
async function delete_photo() {
  try {
    await call_api("DELETE", "photo", {
        id: model.value.images[model.value.show_local_id]["id"]
    });
    error_message.value = null;
    model.value.images.splice(model.value.show_local_id, 1);
    // switch to the other image if any
    if (model.value.show_local_id>0) left();
    else if (model.value.images.length==0) cancel();
  } catch (error) {
      error_message.value = error;
  }
  hide_options(null, true);
}

// move between the photos with the keybord right/left keys.
onMounted(() =>
addEventListener("keydown", function(event){
    if (changing_caption.value) return;
    else if(event.key=="ArrowLeft"){
      left();
    }
    else if (event.key=="ArrowRight") {
      right();
    }
}));
</script>

<style>
.image {
  max-width: 60%;
  max-height: 70%;
  margin: auto;
  z-index: 5;
}
.fullscreen {
  width: 100vw;
  height: 100vh;
  display: flex;
}
.close_btn {
  position: absolute;
  top: 30px;
  right: 30px;
}
.left_btn {
  position: absolute;
  left: 30px;
  top: calc(50% - 32px);
}
.right_btn {
  position: absolute;
  right: 30px;
  top: calc(50% - 32px);
}
.caption {
  position: absolute;
  font-size: 24px;
  color: #fff;
  bottom: 50px;
  left: 0;
  right: 0;
  width: fit-content;
  max-width: 70%;
  margin-right: auto;
  margin-left: auto;
  display: block;
  background: #0000007a;
}
.options_open {
  position: absolute;
  top: 35px;
  right: 119px;
}
.side-alert {
  position: absolute;
  bottom: 5px;
  right: 10px;
}
#options, #album_selection {
  display: block;
}
.loading_dots {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
}
</style>

<template>
  <div v-if="model.show_local_id!=null" class="modal black_cover fullscreen" tabindex="-1">
    <div class="side-alert alert alert-danger" role="alert" :hidden="error_message==null">
        <small>{{ error_message }}</small>
    </div>
    <a class="close_btn" @click="cancel">
      <svg xmlns="http://www.w3.org/2000/svg" height="64px" viewBox="0 -960 960 960" width="64px" fill="#FFFFFF"><path d="m256-200-56-56 224-224-224-224 56-56 224 224 224-224 56 56-224 224 224 224-56 56-224-224-224 224Z"/></svg>
    </a>
    <a class="left_btn" @click="left" :hidden="model.show_local_id==0">
      <svg xmlns="http://www.w3.org/2000/svg" height="64px" viewBox="0 -960 960 960" width="64px" fill="#FFFFFF"><path d="M400-80 0-480l400-400 71 71-329 329 329 329-71 71Z"/></svg>
    </a>
    <a class="right_btn" @click="right" :hidden="model.show_local_id==model.images.length-1">
      <svg xmlns="http://www.w3.org/2000/svg" height="64px" viewBox="0 -960 960 960" width="64px" fill="#FFFFFF"><path d="m321-80-71-71 329-329-329-329 71-71 400 400L321-80Z"/></svg>
    </a>
    <a class="options_open" @click="show_hide_options">
      <svg xmlns="http://www.w3.org/2000/svg" height="54px" viewBox="0 -960 960 960" width="54px" fill="#FFFFFF"><path xmlns="http://www.w3.org/2000/svg" d="M480-160q-33 0-56.5-23.5T400-240q0-33 23.5-56.5T480-320q33 0 56.5 23.5T560-240q0 33-23.5 56.5T480-160Zm0-240q-33 0-56.5-23.5T400-480q0-33 23.5-56.5T480-560q33 0 56.5 23.5T560-480q0 33-23.5 56.5T480-400Zm0-240q-33 0-56.5-23.5T400-720q0-33 23.5-56.5T480-800q33 0 56.5 23.5T560-720q0 33-23.5 56.5T480-640Z"/></svg>
    </a>
    <p class="caption">{{ model.show_local_id==null ? '' : model.images[model.show_local_id]['caption'] }}</p>
    <div class="loading_dots"></div>
    <img class="image" v-if="model.show_local_id!=null" :src="get_image_path()">
    <div class="dropdown-menu" id="options" aria-labelledby="dropdownMenuButton" @mouseleave="hide_options" :hidden="!show_options">
      <a class="dropdown-item" @click="move">
        <svg class="me-2 mb-1" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="m488-400-65 65 56 56 161-161-161-161-56 56 65 65H320v80h168ZM160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h240l80 80h320q33 0 56.5 23.5T880-640v400q0 33-23.5 56.5T800-160H160Zm0-80h640v-400H447l-80-80H160v480Zm0 0v-480 480Z"/></svg>
        Move to another album
      </a>
      <a class="dropdown-item" @click="change_caption">
        <svg class="me-2 mb-1" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="M200-200h57l391-391-57-57-391 391v57Zm-80 80v-170l528-527q12-11 26.5-17t30.5-6q16 0 31 6t26 18l55 56q12 11 17.5 26t5.5 30q0 16-5.5 30.5T817-647L290-120H120Zm640-584-56-56 56 56Zm-141 85-28-29 57 57-29-28Z"/></svg>
        Change caption
      </a>
      <a class="dropdown-item" @click="download_image">
        <svg class="me-2 mb-1" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="M480-320 280-520l56-58 104 104v-326h80v326l104-104 56 58-200 200ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z"/></svg>
        Download image
      </a>
      <a class="dropdown-item" @click="download_metadata">
        <svg class="me-2 mb-1" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000"><path d="M480-480ZM202-65l-56-57 118-118h-90v-80h226v226h-80v-89L202-65Zm278-15v-80h240v-440H520v-200H240v400h-80v-400q0-33 23.5-56.5T240-880h320l240 240v480q0 33-23.5 56.5T720-80H480Z"/></svg>
        Download metadata
      </a>
      <a class="dropdown-item" @click="delete_photo">
        <svg class="me-2 mb-1" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="M280-120q-33 0-56.5-23.5T200-200v-520h-40v-80h200v-40h240v40h200v80h-40v520q0 33-23.5 56.5T680-120H280Zm400-600H280v520h400v-520ZM360-280h80v-360h-80v360Zm160 0h80v-360h-80v360ZM280-720v520-520Z"/></svg>
        Delete photo
      </a>
    </div>
    <div class="dropdown-menu" id="album_selection" aria-labelledby="dropdownMenuButton" @mouseleave="hide_options" :hidden="!show_album_selection">
      <a class="dropdown-item" v-for="album in albums" @click="move_to(album['id'])">
        <svg class="me-2 mb-1" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#000000"><path d="M160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h240l80 80h320q33 0 56.5 23.5T880-640v400q0 33-23.5 56.5T800-160H160Zm0-80h640v-400H447l-80-80H160v480Zm0 0v-480 480Z"/></svg>
        {{ album["name"] }}
      </a>
    </div>
    <div :hidden="!changing_caption" class="modal black_cover" tabindex="-1" @click="stop_changing_caption">
      <div class="modal-dialog" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Change caption</h5>
            <button type="button" @click="stop_changing_caption" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="alert alert-danger" role="alert" :hidden="caption_error_message==null">
              <small>{{ caption_error_message }}</small>
          </div>
          <div class="alert alert-success" role="alert" :hidden="caption_success_message==null">
              <small>{{ caption_success_message }}</small>
          </div>
          <div class="modal-body">
            <form class="form-control-lg">
                <div class="form-group">
                    <textarea class="form-control my-3" type="text" id="new_caption" placeholder="Enter new caption"
                     :value="model.show_local_id==null ? '' : model.images[model.show_local_id]['caption']">
                    </textarea>
                </div>
                <div class="form-group text-end mt-4">
                    <input class="btn btn-primary" type="button" value="Update" @click="submit_caption">
                </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>

</template>