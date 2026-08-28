<script setup>
import { ref } from 'vue';
import { call_api } from "../../assets/API.js";

/** Vue model that contains reactive object with at least two following fields:
 * * albums - reactive component with list of albums,
 *            where album is represented as the object with at least two following fields:
 *     * id - id of the album
 *     * name - name of the album
 * * delete_local_index - integer or null object that specifies what album was requested
 *                        to be deleted. If null no object needs to be deleted and dialog
 *                        should be hidden. If integer, then it specifies the index
 *                        of the item in the albums list (it is not the index specified inside
 *                        album object).
 */
const model = defineModel();

/** Error message to be displayed. Not displayed when null. */
const error_message = ref(null);
/** Success message to be displayed. Not displayed when null. */
const success_message = ref(null);

/**
 * Hides current dialog by resseting all values and setting model.delete_local_index
 * to null.
 */
function hide_dialog() {
  model.value.delete_local_index = null;
  error_message.value = null;
  success_message.value = null;
}

/**
 * Confirms the deletion of the album provided in the model.delete_local_index.
 * If successful, shows success message, in 0.7s removes album from model.albums
 * is removed and the dialog disappears, additionaly, if this album is currently
 * opened (currend address is "#<deleted id>"), then user is redirected to "/".
 * If error happens during the operation, then it is shown to the user.
 */
async function confirm_album_deletion() {
    try {
        await call_api("DELETE", "album", {
            id: model.value.albums[model.value.delete_local_index]["id"]
        });
        error_message.value = null;
        success_message.value = "The album was successfully deleted.";
        await new Promise(r => setTimeout(r, 700));
        if (window.location.hash.slice(1)==model.value.albums[model.value.delete_local_index]["id"]) {
            window.location.replace("#");
        }
        model.value.albums.splice(model.value.delete_local_index, 1)
        hide_dialog();
    } catch (error) {
        error_message.value = error;
    }
}
</script>

<template>
  <div :hidden="model.delete_local_index==null" class="modal black_cover" tabindex="-1" style="display: block;" @click="hide_dialog">
      <div class="modal-dialog" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Delete album</h5>
            <button type="button" @click="hide_dialog" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="alert alert-danger" role="alert" :hidden="error_message==null">
              <small>{{ error_message }}</small>
          </div>
          <div class="alert alert-success" role="alert" :hidden="success_message==null">
              <small>{{ success_message }}</small>
          </div>
          <div class="modal-body">
            <h5 for="album_name" v-if="model.delete_local_index!=null">
                Are you sure you want to delete album "{{ model.albums[model.delete_local_index]["name"] }}"?
            </h5>
            <div class="form-group text-end mt-4">
                <input class="btn btn-secondary me-2" type="button" value="Cancel" @click="hide_dialog">
                <input class="btn btn-primary" type="button" value="Confirm" @click="confirm_album_deletion">
            </div>
          </div>
        </div>
      </div>
    </div>

</template>