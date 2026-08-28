<script setup>
import { onMounted, reactive, ref } from 'vue';
import { call_api, get_image } from '../assets/API.js'
import ImageViewer from './ImageViewer.vue';

const search_prefix = "search:";
/** Error message to be displayed. Not displayed when null. */
const error_message = ref(null);
/** The hash value of the current url. First "#" symbol is excluded if presented. */
const current_hash = ref(window.location.hash.slice(1));
/** Reactive list of all images that should be shown in the gallery.
 * Each image is represented by the dictionary with the following fields:
 * * id - integer id of the photo
 * * caption - string description of the photo
 * * album - integer id of the album current photo belongs to
 * * date - uploading date of the image
 * * name - original name of the uploaded file
 * * src - the path to the image file
 */
const images = reactive([]);
/** Search query that is currently being searched. Null user does no search right now. */
const search_query = ref(null);
/** Boolean reference. True if more images is currently loaded, False if currently no more
 * images are loaded.
 */
const loading = ref(false);
/** Empty response with 0 images was obtained meaning end is reached. */
const loading_finished = ref(false);

/** How many times load function should be executed. Increases when there is
 * a call to the load function which is already loading something.
 * Together with "loading" acts as a simplified locking system.
 */
var repeat_loading = 0;

/**
 * Loads more images from API with the required offset.
 * If no images are returned than end is reached and stop doing any further requests
 * until page updates or redirection happens. Only one load function can be executed
 * at a time, calling it again while the previous call still executing will result
 * in an immediate return of the second call and first call when finished will
 * run the function one more time. For this reason the user should not rely on Promise
 * object returned by the function if multithreading is used or some calls to load are not
 * awaited.
 */
async function load() {
  // stop if end was reached
  if (loading_finished.value) return;
  // if load is already executed increase queue number
  if (loading.value) {
    repeat_loading++;
    return;
  }
  // lock
  loading.value = true;
  // save old hash to interrupt execution when it changes
  let old_hash = current_hash.value;
  const offset = images.length;

  try {
    var response_data = null;
    if (search_query.value==null) {
      if (current_hash.value=="") {
        response_data = await call_api("GET", "photo?offset=" + offset, null);
      } else {
        response_data = await call_api("GET", "photo?offset=" + offset + "&id=" + current_hash.value, null);
      }
    } else {
      response_data = await call_api("GET", "search/" + encodeURI(search_query.value) + "?offset=" + offset, null);
    }

    // check if end is reached
    if (response_data.length==0) {
      loading_finished.value = true;
    }

    for (let image of response_data) {
      image["src"] = await get_image(image["id"], true);
      // check if hash is still the same, if not current data is
      // not the one user needs anymore
      if (old_hash!=current_hash.value) {
        loading.value = false;
        if (repeat_loading>0) {
          repeat_loading--;
          load();
        }
        return;
      }
      images.push(image);
    }
  } catch (error) {
    error_message.value = error;
  }
  
  loading.value = false;
  // repeat loading if something is in queue
  if (repeat_loading>0) {
    repeat_loading--;
    load();
  }
}


/**
 * Updates the page by resetting all required values and loads the first batch of images.
 */
async function update() {
  error_message.value = null;
  search_query.value = null;
  loading_finished.value = false;
  current_hash.value = window.location.hash.slice(1);
  while(images.length>0) images.pop();
  if (current_hash.value.slice(0, search_prefix.length)==search_prefix) {
    search_query.value = decodeURI(current_hash.value.slice(search_prefix.length));
    document.getElementById("search").value = search_query.value;
  } else {
    document.getElementById("search").value = "";
  }
  load();
}


/** Starts search with entered value in the search bar. Done by redirecting user to the search page
 * by changing hash. */
function search() {
  search_query.value = document.getElementById("search").value;
  window.location.href = "#" + search_prefix + search_query.value;
}

/** Vue model for ImageViewer in accordance with ImageViewer.model documentation. */
const image_viewer_data = reactive({
  images: images,
  show_local_id: null,
  loading_fn: load
});

/**
 * Displays the selected photo using ImageViewer.
 * @param local_id Position of the selected photo in the "images" list.
 */
function display_image(local_id) {
  image_viewer_data.show_local_id = local_id;
}

// update gallery at every hash change
onMounted(() => {
  window.addEventListener('hashchange', update);
});
onMounted(update);
// load more content when end is reached
onMounted(() => {
  const options = {
    root: document.getElementById("img_gallery"),
    rootMargin: "0px",
    scrollMargin: "100px",
    threshold: 0.0,
  };

  const observer = new IntersectionObserver(load, options);
  observer.observe(document.getElementById("loader"));
});
</script>

<style>
.gallery_image {
  max-height: 150px;
  padding: 10px;
  cursor: pointer;
}
.gallery_image:hover {
  opacity: 80%;
  box-shadow: 0px 0px 10px 10px #eee;
}
.gallery {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
}
#end_space {
  max-height: 150px;
  padding: 10px;
  flex: auto;
}
</style>

<template>
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="search-container">
        <input type="text" id="search" class="form-control search-input" placeholder="Search..." @keyup.enter="search">
      </div>
    </div>
  </div>
  <div>
    <div class="gallery mt-3" id="img_gallery">
      <img v-for="(image, i) in images" :key="image['id']" :alt="image['caption']"
                                        :src="image['src']" class="gallery_image" @click="display_image(i)">
      <div id="end_space"></div>
    </div>
    <div class="alert alert-danger m-5 mt-3" role="alert" :hidden="error_message==null">
      <h4 class="alert-heading">Unable to load the content</h4>
      <p>{{ error_message }}</p>
    </div>
    <div class="alert alert-secondary m-5 mt-3" role="alert" :hidden="images.length>0 || !loading_finished">
      <h4 class="alert-heading">There is nothing to show here yet</h4>
      <p>Currently there are no images to show here. Try to upload more images.</p>
    </div>
  </div>
  <div class="loading_dots" id="loader" :hidden="!loading"></div>
  <ImageViewer v-model="image_viewer_data"/>
</template>