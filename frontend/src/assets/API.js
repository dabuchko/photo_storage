const UNKNOWN_ERROR_MESSAGE = "Unknown error happened. Please try again later.";

/**
 * Processes http response extracting response status and json body.
 * If error happens during extracting the response body as JSON object or
 * response code is not 200, the corresponding error is thrown as a String object.
 * @param {Response} response The response object of the HTTP request.
 * @returns JSON body of the response.
 */
async function process_response(response) {
    let status = response.status;
    let data = {};
    try {
        data = await response.json();
    } catch {
        throw UNKNOWN_ERROR_MESSAGE;
    }

    if (status==200) {
        return data
    } else if (status==400 && data.hasOwnProperty("error")) {
        throw data["error"];
    } else if (status==401 && data["authenticated"]) {
        localStorage.removeItem("auth_token");
        window.location.replace("/login");
        throw "Unathenticated.";
    } else {
        throw UNKNOWN_ERROR_MESSAGE;
    }
}

/**
 * Sends login request to API. If credentials are entered correctly then
 * authorization token, returned from API, is saved to local storage under
 * "auth_token" name. If credentials do not match then false is returned.
 * If other error is occured, the corresponding String message is thrown.
 * @param {String} username User's username.
 * @param {String} password User's password.
 * @returns True if successfully logged in, false otherwise.
 */
export async function login(username, password) {
    const options = {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            username: username,
            password: password
        })
    };
    const response = await fetch(__API_BASE__ + "user/login", options);
    let status = response.status;
    let data = {};
    try {
        data = await response.json();
    } catch {
        throw UNKNOWN_ERROR_MESSAGE;
    }
    if (status==200) {
        localStorage.setItem("auth_token", data["auth_token"]);
        return true;
    } else if (status==401) {
        return false;
    } else if (status==400 && data.hasOwnProperty("error")) {
        throw data["error"];
    } else {
        throw UNKNOWN_ERROR_MESSAGE;
    }
}

/**
 * Sends signup request to API. If credentials are entered correctly then
 * authorization token, returned from API, is saved to local storage under
 * "auth_token" name. Otherwise the corresponding error is thrown.
 * If other error is occured, it is thrown as a String object.
 * @param {*} username User's username.
 * @param {*} password User's password.
 */
export async function signup(username, password) {
    const options = {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            username: username,
            password: password
        })
    };
    const response = await fetch(__API_BASE__ + "user/signup", options);
    let status = response.status;
    let data = {};
    try {
        data = await response.json();
    } catch {
        throw UNKNOWN_ERROR_MESSAGE;
    }
    if (status==200) {
        localStorage.setItem("auth_token", data["auth_token"]);
    } else if (status==400 && data.hasOwnProperty("error")) {
        throw data["error"];
    } else {
        throw UNKNOWN_ERROR_MESSAGE;
    }
}

/**
 * Sends request to API for authenticated users where JSON response is expected.
 * If error happened or unexpected response received, the corresponding error thrown as a String object.
 * @param {String} method HTTP method of the API request.
 * @param {String} path Relative path to the API endpoint.
 * @param {Object} data Data in the JSON format that will be submitted in request body.
 * @returns JSON body of the response.
 */
export async function call_api(method, path, data) {
    const options = {
        method: method.toUpperCase(),
        headers: {
            'Content-Type': 'application/json',
            'Authorization': localStorage.getItem("auth_token")
        }
    };
    if (data !== null) {
        options.body = JSON.stringify(data);
    }
    const response = await fetch(__API_BASE__ + path, options);
    return process_response(response);
}

/**
 * Uploads new photos to the API endpoint /photo using PUT method, according
 * to the API documentation.
 * If error happened or unexpected response received, the corresponding error thrown as a String object.
 * @param {File} files A list of files that are uploaded to the /photo API endpoint.
 * @returns JSON body of the response.
 */
export async function upload_files(files) {
    var formData = new FormData();
    for (var i = 0; i < files.length; i++) {
        formData.append("file[]", files[i]);
    }
    const options = {
        method: "PUT",
        headers: {
            'Authorization': localStorage.getItem("auth_token")
        },
        body: formData
    };
    const response = await fetch(__API_BASE__ + "photo", options);
    return process_response(response);
}

/**
 * Requests image file from API endpoint /image according to the API documentation
 * and returns link to it.
 * If error happened or unexpected response received, the corresponding error thrown as a String object.
 * @param {Number} id ID of the requested image.
 * @param {boolean} thumbnail True if downscaled thumbnail should be loaded instead of the full-size image.
 * @returns Link to the image file stored locally at blob://. If error
 * occured during loading, null will be returned.
 */
export async function get_image(id, thumbnail = false) {
    const image_link = __API_BASE__ + "image/" + Number(id) + (thumbnail ? "?thumbnail" : "");
    const options = {
        method: "GET",
        headers: {'Authorization': localStorage.getItem("auth_token")}
    };
    const response = await fetch(image_link, options);
    if (response.status==200) {
        return URL.createObjectURL(await response.blob());
    } else {
        return null;
    }
}