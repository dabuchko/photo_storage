<script setup>
import { ref } from 'vue';
import { call_api } from "../../assets/API.js";

/** Vue model that contains reactive object with at least two following fields:
 * * albums - reactive component with list of albums,where each album is
 *            represented as the object with at least two following fields:
 *     * id - id of the album
 *     * name - name of the album
 * * rename_local_index - integer or null object that specifies what album was requested
 *                        to be renamed. If null, no object needs to be renamed and dialog
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
 * Hides current dialog by resseting all values and setting model.rename_local_index
 * to null.
 */
function hide_dialog() {
  model.value.rename_local_index = null;
  error_message.value = null;
  success_message.value = null;
}

/**
 * Renames the album provided in the model.rename_local_index, with name
 * from the form. If successful, shows success message, in 0.7s changes the
 * album name in model.albums, then dialog disappears.
 * If error happens during the operation, then it is shown to the user.
 */
async function rename_album() {
    let album_name = document.getElementById("album_name").value;
    try {
        await call_api("UPDATE", "album", {
            id: model.value.albums[model.value.rename_local_index]["id"],
            name: album_name
        });
        error_message.value = null;
        success_message.value = "The album was successfully renamed.";
        await new Promise(r => setTimeout(r, 700));
        model.value.albums[model.value.rename_local_index]["name"] = album_name;
        hide_dialog();
    } catch (error) {
        error_message.value = error;
    }
}
</script>

<template>
  <div :hidden="model.rename_local_index==null" class="modal black_cover" tabindex="-1" @click="hide_dialog">
      <div class="modal-dialog" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Rename album</h5>
            <button type="button" @click="hide_dialog" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="alert alert-danger" role="alert" :hidden="error_message==null">
              <small>{{ error_message }}</small>
          </div>
          <div class="alert alert-success" role="alert" :hidden="success_message==null">
              <small>{{ success_message }}</small>
          </div>
          <div class="modal-body">
            <form class="form-control-lg">
                <div class="form-group">
                    <input v-if="model.rename_local_index!=null" class="form-control my-3" type="text" id="album_name"
                    placeholder="Enter new album name" title="Only lowercase Latin letters and numbers are allowed"
                    :value="model.albums[model.rename_local_index]['name']">
                </div>
                <div class="form-group text-end mt-4">
                    <input class="btn btn-primary" type="button" value="Update" @click="rename_album">
                </div>
            </form>
          </div>
        </div>
      </div>
    </div>

</template>