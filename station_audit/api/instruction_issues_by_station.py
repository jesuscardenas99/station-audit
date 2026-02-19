def doGet(request, session):
    start_date = request['params'].get('start_date')
    end_date = request['params'].get('end_date')
    area_id = request['params'].get('area_id')
    station_id = request['params'].get('station_id')

    shift = request['params'].get('shift')

    data = audit.get_instruction_issues_by_station(start_date, end_date, area_id, station_id, shift)
    return {'json': data}

def get_control_issues_by_station(start_date=None, end_date=None, area_id=None, station_id=None, shift=None, db_connection="NSB_Manufacturing"): 
    sql_query = """
        SELECT TOP 10 a.area_name, s.station_name, s.station_id, COUNT(m.response_id) AS control_issue_count
        FROM qta.manual_control_plan_responses m
        JOIN qta.audits au ON m.audit_id = au.audit_id
        JOIN qta.stations s ON au.station_id = s.station_id
        JOIN qta.areas a ON s.area_id = a.area_id
    """
    where_clauses = ["m.is_issue = 1", "au.plantId = ?"] 
    params = [PLANT_ID]

    if start_date: where_clauses.append("au.audit_date >= ?"); params.append(start_date)
    if end_date: where_clauses.append("au.audit_date <= ?"); params.append(end_date)
    if area_id: where_clauses.append("a.area_id = ?"); params.append(area_id)
    if station_id: where_clauses.append("s.station_id = ?"); params.append(station_id)
    if shift: where_clauses.append("au.shift_audited = ?"); params.append(shift)

    if where_clauses:
        sql_query += " WHERE " + " AND ".join(where_clauses)
    
    sql_query += " GROUP BY a.area_name, s.station_name, s.station_id ORDER BY control_issue_count DESC;"
    
    try:
        results_dataset = system.db.runPrepQuery(sql_query, params, db_connection)
        return _pyDataSetToDictList(results_dataset)
    except Exception as e:
        system.util.getLogger("AuditSystem").error("Error in get_control_issues_by_station: %s" % e)
        return []