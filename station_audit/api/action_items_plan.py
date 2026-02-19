def doGet(request, session):
	items = audit.get_plan_action_items()
	return {'json': items}
