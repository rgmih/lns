_on_ajax_success = function(data) {
	var parsed_data = jQuery.parseJSON(data);
	var container = document.getElementById('container');
	while (container.children.length > 0) {
		container.removeChild(container.firstChild);
	}
	
	for (host in parsed_data) {
		var files = parsed_data[host];
		for (file in files) {
			var isdir = files[file]['isdir'];
			var size = files[file]['size'];

			var new_element = document.createElement('a');
			new_element.textContent = host.toString() + ':  ' + file.toString() + 
				',  directory: ' + isdir.toString() + ',  size: ' + size.toString() + ' bytes';
			container.appendChild(new_element);
			container.appendChild(document.createElement('br'));
		}
	}
	
}

update_entries = function() {
	$.get(
		"/ls",
		_on_ajax_success
	);
};
