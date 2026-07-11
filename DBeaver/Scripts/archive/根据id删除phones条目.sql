SELECT
    p.id,
    c.fn,
    p.number,
    p.types
FROM phones p
JOIN contacts c
    ON p.contact_id = c.id
WHERE p.id IN (${ids})
ORDER BY p.id;

DELETE FROM phones
WHERE id IN (${ids});