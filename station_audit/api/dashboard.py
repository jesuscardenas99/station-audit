def doGet(request, session):
	params = request['params']
	start_date = params.get('start_date')
	end_date = params.get('end_date')
	area_id = params.get('area_id')
	
	if area_id == 'all' or not area_id:
		area_id = None
	else:
		area_id = int(area_id)
		
	dashboard_data = audit.get_dashboard_data(start_date, end_date, area_id)
	return{'json': dashboard_data}