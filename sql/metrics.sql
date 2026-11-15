-- Every assigned customer stays in the denominator (not just visitors/buyers).
SELECT segment, COUNT(*) AS n, SUM(conversion) AS conversions,
       AVG(conversion * 1.0) AS conversion_rate,
       AVG(visit * 1.0) AS visit_rate, AVG(spend) AS revenue_per_customer
FROM customers GROUP BY segment ORDER BY segment;
