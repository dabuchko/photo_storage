<script setup>
import { ref } from 'vue';
import { call_api } from "../assets/API.js";

/** Vue model that contains reference to the boolean value of whether to
 * show settings (true) or not (false). */
const isSettingsOpen = defineModel();

/** Error message to be displayed. Not displayed when null. */
const error_message = ref(null);
/** Success message to be displayed. Not displayed when null. */
const success_message = ref(null);

/**
 * Hides Settings window by resetting all values and setting Vue model value (isSettingsOpen) to false.
 */
function hide() {
  error_message.value = null;
  success_message.value = null;
  isSettingsOpen.value = false;
  document.getElementById("username").value = "";
  document.getElementById("password").value = "";
}

/**
 * Updates username. Activated on submitting "Update username" form.
 * Sends API UPDATE request to the /user endpoint. If updated successfully,
 * the message of successful update will be shown and in 0.7s Settings will be
 * hidden. If update was not successful the corresponding error will be shown.
 */
async function update_username() {
  try {
    var username = document.getElementById("username").value;
    const response_data = await call_api("UPDATE", "user", {
        username: username,
        password: ""
    });
    error_message.value = null;
    document.getElementById("username").value = "";
    success_message.value = "Username successfully updated";
    localStorage.setItem("auth_token", response_data["auth_token"]);
    await new Promise(r => setTimeout(r, 700));
    hide();
  } catch (error) {
    error_message.value = error;
  }
}

/**
 * Updates password. Activated on "Update password" form submission.
 * Sends API update request to /user endpoint updating the password.
 * If updated successfully, the message of successful update will be
 * shown and in 0.7s Settings will be hidden. If update was not
 * successful the corresponding error will be shown.
 */
async function update_password() {
  var password = document.getElementById("password").value;
  try {
    const response_data = await call_api("UPDATE", "user", {
        username: "",
        password: password
    });
    error_message.value = null;
    document.getElementById("password").value = "";
    success_message.value = "Password was successfully updated."
    localStorage.setItem("auth_token", response_data["auth_token"]);
    await new Promise(r => setTimeout(r, 700));
    hide();
  } catch (error) {
    error_message.value = error;
  }
}

/**
 * Downloads metadata of every uploaded photo by the user.
 * It is done by sending POST API request to /photo endpoint.
 * The file with metadata is uploaded in the JSON format.
 * Shows error message if error happened during the process.
 */
async function download_metadata() {
  try {
    const response_data = await call_api("POST", "photo", {ids: "*"});
    // Create a temporary link with downloading content, activate it, delete the link
    var content = JSON.stringify(response_data);
    var uriContent = "data:application/octet-stream," + encodeURIComponent(content);
    const link = document.createElement('a');
    link.href = uriContent;
    link.download = "metadata.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    error_message.value = null;
    success_message.value = null; // if download happened, there is no reason for the additional message
  } catch (error) {
    error_message.value = error;
  }
}

/**
 * Deletes current account by sending DELETE API request to the user.
 * Removes authentiction token from the local storage.
 * If account is deleted successfully, shows success message and redirects to /.
 * If during deletion some error happened, the error is shown to the user.
 */
async function delete_account() {
  try {
    await call_api("DELETE", "user", {});
    error_message.value = null;
    success_message.value = "Account was successfully deleted.";
    localStorage.removeItem("auth_token");
    await new Promise(r => setTimeout(r, 1000));
    window.location.replace("/");
  } catch (error) {
    error_message.value = error;
  }
}
</script>

<template>
  <div :hidden="!isSettingsOpen" class="modal black_cover" tabindex="-1" @click="hide">
      <div class="modal-dialog" @click.stop>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Settings</h5>
            <button type="button" @click="hide" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
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
                    <label for="username">Update username:</label>
                    <input class="form-control my-3" type="text" id="username" placeholder="Enter new username" pattern="[a-z0-9]+"
                    title="Only lowercase Latin letters and numbers are allowed">
                </div>
                <div class="form-group text-end mt-4">
                    <input class="btn btn-primary" type="button" value="Update username" @click="update_username">
                </div>
            </form>
            <form class="form-control-lg my-4">
                <div class="form-group">
                    <label for="password">Update password:</label>
                    <input class="form-control my-3" type="password" id="password" placeholder="Enter new password">
                </div>
                <div class="form-group text-end mt-4">
                    <input class="btn btn-primary" type="button" value="Update password" @click="update_password">
                </div>
            </form>
            <div class="mt-5">
              <hr></hr>
              <button type="button" class="btn btn-info m-3" @click="download_metadata">
                <svg xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="20px" fill="currentColor" class="bi me-1 mb-1">
                  <path d="M480-320 280-520l56-58 104 104v-326h80v326l104-104 56 58-200 200ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z"/>
                </svg>
                Download all metadata
              </button>
              <button type="button" class="btn btn-danger m-3" style="float: right;" @click="delete_account">
                <svg xmlns="http://www.w3.org/2000/svg" height="20px" viewBox="0 -960 960 960" width="20px" fill="currentColor" class="bi me-1 mb-1">
                  <path d="M280-120q-33 0-56.5-23.5T200-200v-520h-40v-80h200v-40h240v40h200v80h-40v520q0 33-23.5 56.5T680-120H280Zm400-600H280v520h400v-520ZM360-280h80v-360h-80v360Zm160 0h80v-360h-80v360ZM280-720v520-520Z"/>
                </svg>
                Delete an account
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

</template>