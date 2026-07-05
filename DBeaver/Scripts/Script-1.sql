SELECT
    p.*
FROM phones p
WHERE p.contact_id IN (
    SELECT id
    FROM contacts
    WHERE fn IN (
        SELECT fn
        FROM contacts
        WHERE TRIM(fn) <> ''
        GROUP BY fn
        HAVING COUNT(*) > 1
    )
)
ORDER BY p.contact_id, p.number;