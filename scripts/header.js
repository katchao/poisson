var FILETYPES = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif'];
var MAX_CONTENT_LENGTH = 16 * 1024 * 1024;
var MAX_IMAGE_UPLOAD_HEIGHT = 1000;
var MAX_IMAGE_UPLOAD_WIDTH = 100;


// validate image file upload
function validate(input) {

	if(jQuery.inArray(input.type, FILETYPES) === -1) { // check filetype
		alert("File is the wrong type");
		$("#submit").prop("disabled", true);
		return false;
	}

	else if(input.size > MAX_CONTENT_LENGTH) { // check file size
		alert("File is too large");
		$("#submit").prop("disabled", true);
		return false;
	}

	else {
		return true;
	}
	
}