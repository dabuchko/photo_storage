<script setup>
import { call_api } from "../assets/API.js";
import { ref, onMounted, reactive } from "vue";
import DeleteAlbum from './album_managment/DeleteAlbum.vue'
import RenameAlbum from './album_managment/RenameAlbum.vue'
import Settings from './Settings.vue'
import Upload from './Upload.vue'

/** The hash value of the current url. First "#" symbol is excluded if presented. */
const current_hash = ref(window.location.hash.slice(1));

// updates current_hash when the hash of the url changes.
onMounted(() => {
  window.addEventListener('hashchange',
    (_) => {
      current_hash.value = window.location.hash.slice(1)
    }
  )
});

/** Reactive list of all albums where each album is represented as dictionary with
 * id and name. "id" is integer, "name" is string. If any changes occur to the
 * albums, this list must be updated.
 */
const albums = reactive([]);
/** If options menu is displayed for some album then reference contains the index
 * of the album object in albums list for which the options menu is displayed for.
 * Null if options menu is not displayed for any album.
 */
const options_local_selected = ref(null);
/** Vue model that stores data for DeleteAlbum in accordance with DeleteAlbum.model documentation. */
const delete_album_data = reactive({albums: albums, delete_local_index: null});
/** Vue model that stores data for RenameAlbum in accordance with RenameAlbum.model documentation. */
const edit_album_data = reactive({albums: albums, rename_local_index: null});
/** Vue model that stores data for Settings in accordance with Settings.isSettingsOpen documentation. */
const isSettingsOpen = ref(false);
/** Vue model that stores data for Upload in accordance with Upload.model documentation. */
const upload_data = reactive({albums: albums, show: false});

/** Displays upload dialog from Upload component. */
function show_upload() {
  upload_data.show = true;
}

/** Displays settings dialog from Settings component. */
function show_settings() {
  isSettingsOpen.value = true;
}

/**
 * Shows (when hidden) or hides (when shown) options menu for the selected album.
 * If options are already shown, but was requested to be shown for the other album,
 * then options for the previous album are hidden and shown for the 
 * @param event Clicking event, from which click position is extracted to show
 * options menu near the current mouse position.
 * @param id The position of the selected album in the albums list.
 */
function show_hide_options(event, id) {
  if (options_local_selected.value==id) {
    options_local_selected.value = null;
  } else {
    options_local_selected.value = id;
  }
  var el = document.getElementById('album_options');
  el.style.top = (event.clientY-5) + "px";
  el.style.left = (event.clientX-5) + "px";
}

/**
 * Hides the options menu if shown for any of the albums.
 */
function hide_options() {
  options_local_selected.value = null;
}

/**
 * Creates a new album with the free name.
 * The free name is selected by sequentially iterating through
 * the album names generated as follows: New album, New album 1,
 * New album 2, ...
 */
async function create_album() {
  // Sequentially find free album name of the form:
  // New album, New album 1, New album 2, ...
  var exist = true;
  var index = -1;
  let name = "";
  while (exist) {
    index++;
    exist = false;
    name = "New album";
    if (index>0) {
      name = name + " " + index;
    }
    for (let album of albums) {
      if (album["name"]==name) {
        exist = true;
        break;
      }
    }
  }
  // API request to create a new album with free name selected before
  try {
    const response_data = await call_api("PUT", "album", {
        name: name
    });
    albums.push({id: response_data["id"], name: name});
  } catch (error) { /* no change will signalize that album was not created. */}
}

/**
 * Requests a list of user's albums from API and pushes them to the
 * "albums" list in a format defined in "albums" variable.
 */
async function load_albums() {
  try {
    const response_data = await call_api("GET", "albums", null);
    for (let item of response_data) {
      item["show_options"] = false;
      albums.push(item);
    }
  } catch (error) { /* do nothing. */}
}

/** Downloads metadata of each photo from the album which options menu is currently displayed. */
async function download_metadata() {
  if (options_local_selected.value!=null) {
    try {
      let response_data = await call_api("POST", "photo", {album: albums[options_local_selected.value]["id"]});
      let data_download_link = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(response_data));
      var a = document.createElement('a');
      a.href = data_download_link;
      a.download = "metadata.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) { /* do nothing. */}
  }
  hide_options();
}

/** Rename album which options menu is currently displayed. */
function rename_album() {
  if (options_local_selected.value!=null) {
    edit_album_data.rename_local_index = options_local_selected.value;
  }
  hide_options();
}

/** Delete album which options menu is currently displayed. */
function delete_album() {
  if (options_local_selected.value!=null) {
    delete_album_data.delete_local_index = options_local_selected.value;
  }
  hide_options();
}

onMounted(load_albums);
</script>

<template>
  <a href="/" class="d-flex align-items-center mb-3 mb-md-0 me-md-auto link-dark text-decoration-none">
    <img src="/logo.svg" class="bi me-2" width="60" height="40">
    <span class="fs-4">Photo Storage</span>
  </a>
  <button type="button" class="btn mb-4 mt-4 btn-outline-primary" @click="show_upload">
    <svg class="bi me-2 mb-1" width="28" height="28" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
      <path xmlns="http://www.w3.org/2000/svg" d="M440-320v-326L336-542l-56-58 200-200 200 200-56 58-104-104v326h-80ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z"/>
    </svg>
    Upload image
  </button>
  <ul class="nav nav-pills flex-column mb-auto" style="overflow-y: scroll;display: block;">
    <li class="nav-item">
      <a href="#" :class="{
        'nav-link': true,
        'active': current_hash=='',
        'link-dark': current_hash!=''
        }" aria-current="page">
        <svg class="bi me-2 mb-1" width="28" height="28" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
          <path d="M240-200h120v-240h240v240h120v-360L480-740 240-560v360Zm-80 80v-480l320-240 320 240v480H520v-240h-80v240H160Zm320-350Z"/>
        </svg>
        Home
      </a>
    </li>
    <li v-for="(album, i) in albums" :hidden="album['name']==''">
      <a :href="'#' + album['id']" :class="{
        'nav-link': true,
        'active': current_hash==album['id'],
        'link-dark': current_hash!=album['id']
        }">
        <svg class="bi me-2 mb-1" width="28" height="28" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
          <path xmlns="http://www.w3.org/2000/svg" d="M360-400h400L622-580l-92 120-62-80-108 140Zm-40 160q-33 0-56.5-23.5T240-320v-480q0-33 23.5-56.5T320-880h480q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H320Zm0-80h480v-480H320v480ZM160-80q-33 0-56.5-23.5T80-160v-560h80v560h560v80H160Zm160-720v480-480Z"/>
        </svg>
        {{ album["name"] }}
        <span id="dropdownMenuButton" @click="show_hide_options($event, i)">
          <svg style="float: right;" xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor">
            <path d="M480-160q-33 0-56.5-23.5T400-240q0-33 23.5-56.5T480-320q33 0 56.5 23.5T560-240q0 33-23.5 56.5T480-160Zm0-240q-33 0-56.5-23.5T400-480q0-33 23.5-56.5T480-560q33 0 56.5 23.5T560-480q0 33-23.5 56.5T480-400Zm0-240q-33 0-56.5-23.5T400-720q0-33 23.5-56.5T480-800q33 0 56.5 23.5T560-720q0 33-23.5 56.5T480-640Z"/>
          </svg>
        </span>
      </a>
      </li>
  </ul>
  <div class="dropdown-menu" id="album_options" aria-labelledby="dropdownMenuButton" style="display: block;" :hidden="options_local_selected==null" @mouseleave="hide_options">
    <a class="dropdown-item" @click="download_metadata">Download metadata</a>
    <a class="dropdown-item" @click="rename_album">Rename</a>
    <a class="dropdown-item" @click="delete_album">Delete</a>
  </div>
  <hr>
  <ul class="d-flex nav nav-pills flex-column">
    <li>
      <button @click="create_album" class="nav-link link-dark">
        <svg class="bi me-2 mb-1" width="28" height="28" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
          <path xmlns="http://www.w3.org/2000/svg" d="M440-440H200v-80h240v-240h80v240h240v80H520v240h-80v-240Z"/>
        </svg>
        Create a new album
      </button>
    </li>
    <li>
      <button @click="show_settings" class="nav-link link-dark">
        <svg class="bi me-2 mb-1" width="28" height="28" xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor">
          <path d="m370-80-16-128q-13-5-24.5-12T307-235l-119 50L78-375l103-78q-1-7-1-13.5v-27q0-6.5 1-13.5L78-585l110-190 119 50q11-8 23-15t24-12l16-128h220l16 128q13 5 24.5 12t22.5 15l119-50 110 190-103 78q1 7 1 13.5v27q0 6.5-2 13.5l103 78-110 190-118-50q-11 8-23 15t-24 12L590-80H370Zm70-80h79l14-106q31-8 57.5-23.5T639-327l99 41 39-68-86-65q5-14 7-29.5t2-31.5q0-16-2-31.5t-7-29.5l86-65-39-68-99 42q-22-23-48.5-38.5T533-694l-13-106h-79l-14 106q-31 8-57.5 23.5T321-633l-99-41-39 68 86 64q-5 15-7 30t-2 32q0 16 2 31t7 30l-86 65 39 68 99-42q22 23 48.5 38.5T427-266l13 106Zm42-180q58 0 99-41t41-99q0-58-41-99t-99-41q-59 0-99.5 41T342-480q0 58 40.5 99t99.5 41Zm-2-140Z"/>
        </svg>
        Settings
      </button>
    </li>
  </ul>
  <DeleteAlbum v-model="delete_album_data"/>
  <RenameAlbum v-model="edit_album_data"/>
  <Settings v-model="isSettingsOpen"/>
  <Upload v-model="upload_data"/>
</template>