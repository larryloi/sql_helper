
DECLARE @BatchSize INT = 1000;  
DECLARE @StartDate DATETIME = '2025-01-01';
DECLARE @EndDate   DATETIME = '2025-02-01';
DECLARE @Slip_id BIGINT;

-- Cursor over Slip_id from source table in date range
DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
    SELECT Slip_id
    FROM [LINKEDSRC_STAGING_GM].[data-ingestion-cms].[DW_ETL].[Table_Rating] WITH (NOLOCK)
    WHERE transaction_datetime >= @StartDate
      AND transaction_datetime < @EndDate
    ORDER BY Slip_id;

OPEN cur;

FETCH NEXT FROM cur INTO @Slip_id;

WHILE @@FETCH_STATUS = 0
BEGIN

    INSERT INTO dbo.Table_Rating_sink (Slip_id, ......, transaction_datetime)
    SELECT TOP (@BatchSize) Slip_id, ......, transaction_datetime
    FROM [LINKEDSRC_STAGING_GM].[data-ingestion-cms].[DW_ETL].[Table_Rating] WITH (NOLOCK)
    WHERE Slip_id >= @Slip_id
      AND transaction_datetime >= @StartDate
      AND transaction_datetime < @EndDate
    ORDER BY Slip_id;

    -- Advance cursor
    FETCH NEXT FROM cur INTO @Slip_id;
END

CLOSE cur;
DEALLOCATE cur;
