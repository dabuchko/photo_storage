<script setup>
import { ref } from 'vue'
import { login } from "../assets/API.js"

/**
 * Warning message to show above login form. Hidden when null.
 */
const message = ref(null)

/**
 * Submits HTML login form. Loads values from the corresponding form fields
 * and sends login API request.
 */
async function submit() {
    var username = document.getElementById("username").value;
    var password = document.getElementById("password").value;
    try {
        const logged_in = await login(username, password);
        if (logged_in) {
            message.value = null;
            window.location.replace("/app");
        } else {
            message.value = "Invalid username or password."
        }
    } catch (error) {
        message.value = error;
    }
}
</script>

<template>
  <form class="form-control-lg">
        <div class="alert alert-danger" role="alert" :hidden="message==null">
            <small>{{ message }}</small>
        </div>
        <div class="form-group">
            <label for="username">Username:</label>
            <input class="form-control" type="text" id="username" placeholder="Enter username" pattern="[a-z0-9]+"
            title="Only lowercase Latin letters and numbers are allowed">
        </div>
        <div class="form-group my-3">
            <label for="password">Password:</label>
            <input class="form-control" type="password" id="password" placeholder="Password">
        </div>
        <small class="text-muted">Do not have an account yet? <a href="/signup">Sign up</a></small>
        <div class="form-group text-end mt-3">
            <input class="btn btn-primary" type="button" value="Login" @click="submit">
        </div>
    </form>
</template>