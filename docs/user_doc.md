# Photo Storage - User Documentation

To start the application follow the installation steps specified in [README.md](../README.md).

Once the application is started the user can access the web application at http://localhost:80/
by default, unless the port settings were changed.

## Registration

To register an account the user must choose username using only small latin letters, numbers
and underscores, and password that should contain 8 symbols and include small and capital
latin letter, number, and at least one special symbol. To register the account the user
must go to the sign up page which can be done by clicking "Sign Up" button at the initial
page, or directly follow http://localhost/signup link. At the registration page the user must
fill the username and password, if registration was successful the user is redirected to
http://localhost/app, otherwise the error will appear. If error appears the user must fix it
and try to submit form again. One of the most common errors is that username is already occupied,
in this case user must choose another username and try to submit form one more time.

## Authorization

If user already has an account, but it is not authenticated, the user may want to log in.
This can be done by clicking "Log In" button at the initial page or by directly following
the link http://localhost/login. At the login page the user must fill the form with
username and password, that correspond to its account, and submit the form. If the
credentials match the existing account the user will be successfully authenticated
and redirected to http://localhost/app, otherwise the error will appear that user should
fix.

## Application

The core of the application functionality is performed at http://localhost/app.
If the user is authorized then it should be able to see a gallery at the right
bottom angle that occupies most of the screen. The gallery contains all images
that are uploaded by the user and fall under some category/criteria. If the user
did not upload any images yet, the gallery will be constantly empty.

The user may choose to show all uploaded images that belong to the user in the
gallery, to do this the user must click on "Home" option at the side panel located at the left.
The user may also choose to show only images that belong to the specific album,
to do this the user must choose the corresponding album at the side panel at the right.
The user may also choose to show the images, caption of which contains some part of the
text, this can be done using the search functionality. To perform search the user
must enter part of the text at the search bar at the top of the page and click "Enter".
After this, gallery will display all images that have in caption the provided part of the text.

### Album managment

The user can create, rename, and delete album. To create a new album, the user
must click on the "Create a new album" button at the bottom of side panel at the
right; after this a new album will be created with name containing "New album",
the created album can be further renamed. To rename the album, the user must
locate the album which needs to be renamed at the side panel at the right,
click on three dots near the album name and choose "Rename" option,
at the popped up window the user can change the name and save the changes,
they will be immediately applied. To delete the album, the user must, again,
click on three dots icon near the album name that should be deleted and choose
"Delete" option; once choosen, the user must confirm album deletion. When album
is deleted, all images in the album disappear.

### Photo uploading

To upload a new image, the user should click on "Upload image" button at the
top of the side panel, located at the right. Then the pop-up with uploading section
will appear, the user can click on the uploading section and choose among local files
images that should be uploaded. The uploading section also supports drag-and-drop.
Every image is uploaded with pre-generated caption and pre-chosen album, the
user can change caption and album in the uploading window. If user made any changes
to caption or album, these changes should be saved by clicking "Save changes"
button at the bottom of the window.

### Photo managment

In the gallery, the user can open the photo in the full-screen mode by clicking on it.
In the full-screen mode the user can navigate among images shown in the screen and
see their caption.
Also the user can choose to perform several actions on the opened image: edit caption,
delete image, download image, download metadata. All this actions can be done by
clicking on three dots and choosing the appropriate option. During image editing
the user must change the caption and click on the "Safe" button. During image
deletion the user must confirm the decision to delete the image. When any
of the download options are chosen the download is started immediately in the JSON format.

### Settings

The user may choose to change username, password, download all metadata, or
delete the account. All this functionality is available in the "Settings" window.
To open the "Settings" window, the user must click on the "Settings" button
at the bottom of the side panel, located at the right. "Settings" window includes
two forms: "Update username", and "Update password". To update username or password,
the user must enter a new username or password to the corresponding form and submit
it. If submission was successful, the pop-up will show success message and close,
otherwise the error message will appear, specifying the error that should be fixed.
The user may also download caption and album name in JSON format, by clicking
"Download all metadata" button. The user may also delete the account by clicking
"Delete the account" button and confirming it choice. 