def doGet(request, session):
	areas = audit.get_active_areas()
	
	return{'json': areas}
