SELECT
    Stream.code,
    Station.latitude,
    Station.longitude
FROM
    Network
        INNER JOIN
    Station ON Network._oid = Station._parent_oid
        INNER JOIN
    SensorLocation ON Station._oid = SensorLocation._parent_oid
        INNER JOIN
    Stream ON SensorLocation._oid = Stream._parent_oid
where
	Network.code = "{net}"
	and Station.code = "{sta}"
    and SensorLocation.code = "{loc}"
    and Stream.code like "{ch}%"
    and Stream.code not like "BH%"
GROUP BY Station.code, SensorLocation.code, Stream.code