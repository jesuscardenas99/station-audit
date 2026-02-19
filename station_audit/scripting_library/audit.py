PLANT_ID = 1

def _pyDataSetToDictList(pyData):
    """Converts a PyDataSet to a list of dictionaries."""
    results = []
    headers = [pyData.getColumnName(i) for i in range(pyData.getColumnCount())]
    for row in pyData:
        rowDict = {}
        for i, header in enumerate(headers):
            rowDict[header] = row[i]
        results.append(rowDict)
    return results
        
def get_plan_action_items(db_connection="NSB_Manufacturing"):
    """Gets all open instruction action items for the selected plant."""
    sql_query = """
        SELECT m.response_id, m.check_description, m.compliance_evidence, m.issues_found, s.station_name, a.audit_date, ar.area_name
        FROM qta.manual_instruction_responses m
        JOIN qta.audits a ON m.audit_id = a.audit_id
        JOIN qta.stations s ON a.station_id = s.station_id
        JOIN qta.areas ar ON s.area_id = ar.area_id
        WHERE m.is_issue = 1 AND m.action_status = 'Open' AND a.plantId = ?
        ORDER BY a.audit_date ASC;
    """
    try:
        results_dataset = system.db.runPrepQuery(sql_query, [PLANT_ID], db_connection)
        return _pyDataSetToDictList(results_dataset)
    except Exception as e:
        system.util.getLogger("AuditSystem").error("Error in get_plan_action_items: %s" % e)
        return []

def add_new_audit(audit_data):
    """Adds a new quality audit to the database for the configured plant."""
    logger = system.util.getLogger("AuditSystem")
    tx = system.db.beginTransaction(database="NSB_Manufacturing")
    try:
        details = audit_data['details']
        notes = audit_data.get('finalNotes', {})
        
        # Calculation
        total_score = sum(resp.get('score', 0) for resp in audit_data['responses'].values())
        max_possible = len(audit_data['responses']) * 2
        quality_percentage = round((total_score / float(max_possible)) * 100, 2) if max_possible > 0 else 0
        
        logger.info("Calculated quality_percentage: %s" % str(quality_percentage))
        
        audit_query = """
            INSERT INTO qta.audits 
            (audit_date, station_id, quality_percentage, qa_tech_username, apu_id, shift_audited,
             notes_outside_scope, notes_special_tasks, notes_incomplete_tasks, audit_type, time_spent, sku, plantId) 
            VALUES (GETDATE(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        audit_args = [
            details.get('station_id'),
            quality_percentage,
            details.get('qa_tech_username'),
            details.get('apu_id'),
            details.get('shift_audited'),
            notes.get('outsideScope'),
            notes.get('specialTasks'),
            notes.get('incompleteTasks'),
            'Quality Audit',
            details.get('timeSpent'),
            details.get('product_sku'),
            PLANT_ID
        ]
        
        logger.info("Arguments for audit insert: %s" % str(audit_args))
        
        new_audit_id = system.db.runPrepUpdate(audit_query, audit_args, tx=tx, getKey=1)
        
        # Insert responses
        response_query = "INSERT INTO qta.audit_responses (audit_id, question_id, score, evidence, plantId) VALUES (?, ?, ?, ?, ?)"
        for q_id, resp in audit_data['responses'].items():
            response_args = [new_audit_id, int(q_id), resp.get('score'), resp.get('evidence'), PLANT_ID]
            system.db.runPrepUpdate(response_query, response_args, tx=tx)
            
        system.db.commitTransaction(tx)
        return new_audit_id
        
    except Exception as e:
        system.db.rollbackTransaction(tx)
        logger.error("Error in add_new_audit", e)
    finally:
        system.db.closeTransaction(tx)
    
def add_instruction_check(check_data, db_connection="NSB_Manufacturing"):
    """Adds a new instruction check and returns its new ID."""
    query = """
        INSERT INTO qta.instruction_checks
        (process, check_text, doc, eval, size, freq, method, react, plantId)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    args = [
        check_data.get('process'), check_data.get('check_text'), check_data.get('doc'),
        check_data.get('eval'), check_data.get('size'), check_data.get('freq'),
        check_data.get('method'), check_data.get('react'), PLANT_ID
    ]
    try:
        new_id = system.db.runPrepUpdate(query, args, db_connection, getKey=1)
        return new_id
    except Exception as e:
        system.util.getLogger("AuditSystem").error("Error in add_instruction_check: " + str(e))
        return None
def get_audit_details_list(start_date=None, end_date=None, area_id=None, station_id=None, shift=None, db_connection="NSB_Manufacturing"):
    """
    Gets a detailed list of individual audits based on the provided filters.
    """
    sql_query = """
        SELECT
            au.audit_id, au.audit_date, ar.area_name, s.station_name,
            au.qa_tech_username, au.shift_audited, au.quality_percentage,
            au.time_spent, au.audit_type, au.sku
        FROM qta.audits au
        LEFT JOIN qta.stations s ON au.station_id = s.station_id
        LEFT JOIN qta.areas ar ON s.area_id = ar.area_id
    """
    where_clauses, params = ["au.audit_type = 'Quality Audit'", "au.plantId = ?"], [PLANT_ID]
  
    if start_date:
        where_clauses.append("CAST(au.audit_date AS DATE) >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("CAST(au.audit_date AS DATE) <= ?")
        params.append(end_date)
    if area_id:
        where_clauses.append("ar.area_id = ?")
        params.append(area_id)
    if station_id:
        where_clauses.append("s.station_id = ?")
        params.append(station_id)
    if shift:
        where_clauses.append("au.shift_audited = ?")
        params.append(shift)

    if where_clauses:
        sql_query += " WHERE " + " AND ".join(where_clauses)
    
    sql_query += " ORDER BY au.audit_date DESC;"
    
    results_dataset = system.db.runPrepQuery(sql_query, params, db_connection)
    return _pyDataSetToDictList(results_dataset) 

def get_dashboard_data(start_date, end_date, area_id=None, db_connection="NSB_Manufacturing"):
    """Gets all stations and their audits for the dashboard, filtered by plant."""
    try:
        stations_query = """
            SELECT s.station_id, s.station_name, s.nickname, s.active, ar.area_name
            FROM qta.stations s
            JOIN qta.areas ar ON s.area_id = ar.area_id
            WHERE s.plantId = ? AND s.active = 1
        """
        station_params = [PLANT_ID]
        if area_id:
            stations_query += " AND s.area_id = ?"
            station_params.append(int(area_id))
        stations_query += " ORDER BY ar.area_name, s.station_name"
        
        stations_dataset = system.db.runPrepQuery(stations_query, station_params, db_connection)
        all_stations = _pyDataSetToDictList(stations_dataset)

        audits_query = """
            SELECT au.* FROM qta.audits au
            WHERE au.plantId = ? AND au.audit_date BETWEEN ? AND ?
        """
        audit_params = [PLANT_ID, start_date, end_date]
        if area_id:
            # Subquery ensures we only select audits from stations in the specified area OF THE CURRENT PLANT
            audits_query += " AND au.station_id IN (SELECT station_id FROM qta.stations WHERE area_id = ? AND plantId = ?)"
            audit_params.extend([int(area_id), PLANT_ID])

        audits_dataset = system.db.runPrepQuery(audits_query, audit_params, db_connection)
        audits_for_period = _pyDataSetToDictList(audits_dataset)

        audits_by_station = {}
        for audit in audits_for_period:
            s_id = audit['station_id']
            audits_by_station.setdefault(s_id, []).append(audit)
        
        for station in all_stations:
            station['audits'] = audits_by_station.get(station['station_id'], [])
            
        return all_stations

    except Exception as e:
        system.util.getLogger("AuditSystem").error("Error in get_dashboard_data: " + str(e))
        return []