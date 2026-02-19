def doGet(request, session):
    params = request['params']
    
    data = audit.get_audit_details_list(
        start_date=params.get('start_date'),
        end_date=params.get('end_date'),
        area_id=params.get('area_id'),
        station_id=params.get('station_id'),
        shift=params.get('shift')
    )
    
    return {'json': data}
