var FILETYPES = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif'];
var MAX_CONTENT_LENGTH = 1 * 1024 * 1024;
var MAX_IMAGE_UPLOAD_HEIGHT = 1000;
var MAX_IMAGE_UPLOAD_WIDTH = 100;


// validate image file upload
function validate(input) {
	if(jQuery.inArray(input.type, FILETYPES) === -1) { // check filetype
		return -1;
	}
	else if(input.size > MAX_CONTENT_LENGTH) { // check file size
		return -2;
	}
	else if (input.width > 1000 || input.height > 1000) { // check file dimensions
		return -3;
	}
	else {
		return 1;
	}
}

function enable(button) {
	button.prop('disabled', false);
}

function disable(button) {
	button.prop('disabled', true);
}

function doneLoading(data) {
	$('#main-content').hide("slide", 300, function() {
		$("#main-content").html(data).show("drop",300);
	});
}