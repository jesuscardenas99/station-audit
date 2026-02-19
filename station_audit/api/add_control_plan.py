def doPost(request, session):
	
	try:
	
		payload = request
		
		data_object = payload.get('data')
		
		check_data = data_object.get('check_data')
		station_ids = data_object.get('station_ids')
		
	
		if not check_data:
			error_msg = "Request failed because the 'check_data' key is missing or empty in the payload."
			
			return {'json': {'success': False, 'error': error_msg}, 'statusCode': 400} # 400 = Bad Request
			
		
		new_check_id = audit.add_instruction_check(check_data)
		
		if new_check_id:
			
			if station_ids is not None:
				success_mapping = audit.update_station_mappings(new_check_id, station_ids)
			return {'json': {'success': True, 'new_id': new_check_id}}
		else:
			return {'json': {'success': False, 'error': 'Failed to create new check in database.'}, 'statusCode': 500}
			
	except Exception as e:
	
		system.util.getLogger("AuditSystem").error("Error in doPost endpoint: %s" % e)
		return {'json': {'success': False, 'error': str(e)}, 'statusCode': 500}
