def doPost(request, session):
	
    try:
        payload = request
        
        data_object = payload.get('data')
        check_id = data_object.get('check_id')

        if check_id is None:
            return {'json': {'success': False, 'error': 'Required field "check_id" was not found in the request.'}}

        success = audit.delete_instruction_check(check_id)
        return {'json': {'success': success}}

    # Catch any unexpected errors
    except Exception as e:
        system.util.getLogger("AuditSystem").error("Error in delete_control_plan doPost: " + str(e))
        return {'json': {'success': False, 'error': 'An unexpected server error occurred.'}}
