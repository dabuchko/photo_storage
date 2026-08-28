# API documention

The api will accept requests and return responses only in JSON format with the content type application/json.
There are 3 type of responses and their codes that can be returned as a response:

1. 400 Bad Request

Returned if either request content wasn't successfully parsed by the server, some required JSON entries are missing,
or some JSON entry is in the wrong format. In this case the response with code 400 is returned with the
following content where `<ERROR>` is replaced by the description of error cause:

```
{
    error: "<ERROR>"
}
```

2. 401 Unauthorized

Request to every api endpoint, except "/user/login" and  "/user/signup",
must be accompanied with the "Authorization" header with Bearer token that
will inform the server whether user is authorized to make given request or not.
In case such token was not provided, expired, or does not have enough permissions
to perform current request the response with code 401 will be returned
with the following content where `<AUTHENTICATED>` is replaced by true if
the provided authorization header valid but does not have enough permissions
to perform given request and false otherwise:

```
{
    authenticated: <AUTHENTICATED>
}
```

3. 200 OK

Otherwise if the request was processed successfully, the response with code 200
is returned. The content of the response is in the JSON format and includes entries
depending on the endpoint. In case endpoint has nothing to return, the empty JSON is returned: `{}`

## Endpoints

The api supports the following endpoints and reqest methods:

### POST /user/signup

Registers a new user.

Accepts only requests in the following form where `<USERNAME>` is replaced by the user's
username and `<PASSWORD>` is replaced by the user's password:

```
{
    username: "<USERNAME>",
    password: "<PASSWORD>"
}
```

In case username is specified in the invalid format, already taken by another user,
or password is specified in the wrong format, the response 400 Bad Request is
returned with the corresponding error.

Otherwise, if the user is registered successfully, the Bearer token, which
can be used in the "Authorization" header for further requests, is returned.

### POST /user/login

Logs in the existing user.

Accepts only requests in the following form where `<USERNAME>` is replaced by the
user's username and `<PASSWORD>` is replaced by the user's password:

```
{
    username: "<USERNAME>",
    password: "<PASSWORD>"
}
```

In case there is no entry in the database with the specified username-password
pair the response 401 Unauthorized response is returned.

Otherwise, if the user is authenticated successfully, the Bearer token,
which can be used in the "Authorization" header for further requests, is returned.

### UPDATE /user

Updates user's information.

Accepts only requests in the following form where `<USERNAME>` is replaced by new
username of the user (use "" or old username directly to keep the old one)
and `<PASSWORD>` is replaced by new password of the user (empty if the old password must remain):

```
{
    username: "<USERNAME>",
    password: "<PASSWORD>"
}
```

In case username is specified in invalid format, already taken by another user,
or password is specified in the wrong format, the response 400 Bad Request
is returned with the corresponding error.

Otherwise, if the user updated its information successfully, the new Bearer token,
which can be used in the "Authorization" header for further requests, is returned.
The previous token is automatically expired.

### DELETE /user

Deletes the user's account.

If the operation was successful returns 200 OK with empty JSON. The Bearer token is automatically expired.

### GET /albums

Returns the list of all albums belonging to the user. The format of the response
is the JSON list with each item having id of the album and album name property.

```
[
    {
        id: <ID of the first user's album>,
        name: <NAME of the first user's album>
    },
    ...
]
```

### PUT /album

Creates a new album.

Accepts only requests in the following form where `<NAME>` is replaced by the name of the new album:

```
{
    name: "<NAME>"
}
```

In case name is specified in the invalid format or already exists, the response
400 Bad Request is returned with the corresponding error.

Otherwise, it returns id of the new album in the JSON format:

```
{
    id: <NEW ID>
}
```

### UPDATE /album

Updates album name.

Accepts only requests in the following form where `<NAME>` is replaced by new name
of the album and `<ID>` is replaced by the id of such album:

```
{
    id: <ID>,
    name: "<NAME>"
}
```

In case name is specified in the invalid format, already exists,
or album with the provided id does not exist, the response 400 Bad Request
is returned with the corresponding error.

In case album exists, but does not belong to the user, still the response with
400 response code will be returned stating "Album not found.".

Otherwise, empty JSON is returned.

### DELETE /album

Deletes an album.

Accepts only requests in the following form where `<ID>` is replaced by the id of the album:

```
{
    id: <ID>
}
```

If id does not exists or exists, but album does not belong to the user returns, then
response with code 400 is returned, describing the errorin its body.
Otherwise, response with code 200 is returned, with empty JSON in the body.

### GET /photo?id=<ID>&offset=<OFFSET>

Gets top 50 photos from the specified album with the given offset or top 50 photos
from any album belonging to the user when `<ID>` is not provided.

The `<ID>` must be replaced with the valid album id. In case no album id is
specified the endpoint will return all photos belonging to the user.
The photos are sorted by date and only at most 50 photos can be retrieved by
single request. If `<OFFSET>` is not specified top 50 photos will be returned,
otherwise endpoint returns top 50 photos with the given offset.

In case if any of two parameters have wrong format they will be ignored.

The response has a format of the JSON list where each element is represented
by a JSON object with photo id, caption, album id where photo is located, and
uploading date.

```
[
    {
        id: <PHOTO ID>,
        caption: <PHOTO CAPTION>,
        album: <ALBUM ID WHERE PHOTO IS LOCATED>,
        date: <UPLOADING DATE>
    },
    ...
]
```

### POST /photo

Returns metadata of the requested photos (ids, captions, uploading dates, album name),
or for all of the photos in the requested album.

Accepts only requests in two following forms where `<IDs>` is replaced by an array of
integers representing identificators of the photos user wants to retrieve and `<ALBUM_ID>`
is replaced by the id of the album from which all photo metadata should be retrieved:

```
{
    ids: <IDs>
}
```

```
{
    album: <ALBUM_ID>
}
```

If `<IDs>` is not an array of integers or `<ALBUM_ID>` is not an integer
the 400 response is returned. In case of
problems with individual photos they are ignored. After successful execution
code 200 with the JSON array of photo metadata is returned.

```
[
    {
        id: <ID>,
        caption: <PHOTO CAPTION>,
        album: <ALBUM NAME>,
        date: <UPLOADING DATE>
    },
    ...
]
```

### PUT /photo

Uploads new photos or zip file with photos inside.

Unlike other endpoints accepts requests in multipart/form-data encoding.
The request must include image files that we want to upload in field "file[]".
Files must have jpeg, jpg, png, gif, or webp extensions and have
the corresponding format. Alternatively a zip file with images of
the previously mentioned formats can be used (files inside a zip file with
unknown formats will be ignored).

If uploading is successful returns 200 and JSON in the response body with
id, caption, date, and album fields for each uploaded photos.
If any of the individually uploaded photos (photos that are not inside a zip file)
has unknown extension then error with code 400 will be returned. 

```
[
    {
        id: <PHOTO ID>,
        caption: <PHOTO CAPTION>,
        album: <ALBUM ID>,
        date: <UPLOADING DATE>
    },
    ...
]
```

### UPDATE /photo

Updates photo caption and album id for the specified photo id.

Accepts only requests in the following form where `<ID>` is replaced by the photo id,
`<CAPTION>` is replaced by the new caption of the photo (old can be used),
and `<ALBUM>` is replaced by the new album id (old can be used):

```
{
    id: <PHOTO ID>,
    caption: "<CAPTION>",
    album: <ALBUM ID>
}
```

If photo id or album id does not exists or does not belong to the user,
or caption has invalid format returns code 400, with the corresponding error.
Otherwise 200 with empty JSON in the body.

### DELETE /photo

Deletes photo with the specified id.

Accepts only requests in the following form where `<ID>` is replaced by the photo id to be deleted:

```
{
    id: <ID>
}
```

If photo id does not exists or does not belong to the user returns code 400,
with the corresponding error. Otherwise, status 200 with empty JSON in the body.

### GET /image/<ID>

Returns image file with the specified image id. If thumbnail GET parameter is set,
then instead of the original image its downscaled version is returned.

`<ID>` must be replaced with valid image id. If image is not found or does not belong to
the user the response with status 400 and the corresponding error is returned.

Image file returned in a format specified in the `Content-Type` header. One of four
formats should be expected: JPEG, PNG, GIF, WEBP.

### GET /search/<QUERY>?offset=<OFFSET>

Gets top 50 photos satisfying the search query with the given offset.

The `<QUERY>` must be replaced with the text search query. In case no query is specified,
the endpoint will return 400 Bad Request response code with the corresponding error in the body.
The photos are sorted by date and only at most 50 photos can be retrieved by a single request.
If `<OFFSET>` is not specified, top 50 photos will be returned, otherwise 50 photos starting
from the given offset will be returned. If the offset is in the wrong format 400 Bad Request
status will be returned with the corresponding error.

The endpoint will make search by finding the exact similarities between query and image captions in the database.