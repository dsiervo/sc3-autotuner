Select distinct 
round(( 6371 * acos(cos(radians("{sta_lat}")) * cos(radians(Origin.latitude_value)) * cos(radians(Origin.longitude_value) - radians("{sta_lon}")) + sin(radians("{sta_lat}")) * sin(radians(Origin.latitude_value)))),2) as radius,
POEv.publicID,
Pick.time_value, Pick.time_value_ms
from Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid 
left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID 
left join Origin ON POOri._oid=Origin._oid left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID 
left join Magnitude ON Magnitude._oid = POMag._oid 
left join Arrival on Arrival._parent_oid=Origin._oid 
left join PublicObject as POOri1 on POOri1.publicID = Arrival.pickID 
left join Pick on Pick._oid= POOri1._oid 
where 
Magnitude.magnitude_value between 1.2 and 3.0 
AND Pick.phaseHint_used = 1 
AND Pick.evaluationMode = "manual" 
AND Arrival.phase_code = "{ph}" 
AND Pick.waveformID_stationCode = "{sta}" 
AND Pick.waveformID_networkCode = "{net}" 
AND Magnitude.magnitude_value IS not NULL 
AND Origin.quality_usedPhaseCount IS not null 
AND (EvMF.type NOT IN ("not locatable", "explosion", "not existing", "outside of network interest") OR EvMF.type IS NULL) 
AND Origin.time_value between "{ti}" and "{tf}"
HAVING radius < {radius}
LIMIT 190