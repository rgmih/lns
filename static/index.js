

update_entries = function() {
	var response_data = new String();
	$.get(
		"/ls",
		function(data) {
			response_data += data.toString();
		}
	);
	
	alert('Refreshed. Response data: ' + response_data);
};
