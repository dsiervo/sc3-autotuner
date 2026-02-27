select
round(( 6371 * acos(cos(radians({sta_lat})) * cos(radians(Origin.latitude_value)) * cos(radians(Origin.longitude_value) - radians({sta_lon})) + sin(radians({sta_lat})) * sin(radians(Origin.latitude_value)))),2) as radius,
POEv.publicID,
A_p.phase_code, pick_p.time_value, pick_p.time_value_ms,
A_s.phase_code, pick_s.time_value, pick_s.time_value_ms
from
Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid
left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID
left join Origin ON POOri._oid=Origin._oid
left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID
left join Magnitude ON Magnitude._oid = POMag._oid
left join Arrival A_p on A_p._parent_oid=Origin._oid  and A_p.phase_code = 'P'
inner join Arrival A_s on A_s._parent_oid=A_p._parent_oid and A_s.phase_code = 'S'
left join PublicObject as POOri1 on POOri1.publicID = A_p.pickID
left join PublicObject as POOri2 on POOri2.publicID = A_s.pickID
left join Pick pick_p on pick_p._oid = POOri1._oid
left join Pick pick_s on pick_s._oid = POOri2._oid
where
#pick_p.phaseHint_used = 1
pick_p.evaluationMode = 'manual'
AND Origin.evaluationStatus in ('final', 'preliminary')
AND pick_s.evaluationMode = 'manual'
AND pick_p.waveformID_stationCode = pick_s.waveformID_stationCode
AND Origin.time_value between "{ti}" and "{tf}"
AND pick_p.waveformID_networkCode = "{net}" 
AND pick_p.waveformID_stationCode = "{sta}" 
AND Magnitude.magnitude_value between "{min_mag}" and "{max_mag}"
HAVING radius < {radius}
order by pick_p.time_value desc
LIMIT {max_picks}
