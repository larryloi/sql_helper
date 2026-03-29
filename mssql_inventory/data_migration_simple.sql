-- ==============================================================================
-- Simple MSSQL Linked Server Batch Migration
-- - Hard-coded source/sink identifiers (edit these in the file if needed)
-- - Only variables exposed: @atime, @btime, @BatchSize
-- - Runs on the sink SQL Server instance
-- - Uses small transactional batches to limit locking
-- ==============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- ======== CONFIGURE (only these three are variables) ========
DECLARE @BatchSize INT = 1000;                         -- rows per batch
DECLARE @atime DATETIME2 = '2025-01-01T00:00:00';      -- start time (inclusive)
DECLARE @btime DATETIME2 = '2025-12-31T00:00:00';      -- end time (exclusive)
-- ===========================================================

-- === HARD-CODED OBJECTS (edit directly here if needed) ===
-- Linked server and source
-- Note: use the actual linked-server, database, schema and table names below
-- Example four-part source: [LINKEDSVR_ABC].[SrcDatabase].[dbo].[SrcTable]
-- Example sink: [TargetDatabase].[dbo].[TargetTable]

-- Source (linked server)
-- Format: [LinkedServer].[Database].[Schema].[Table]
-- Edit the names below if your environment differs
-- (these are hard-coded per your request)
--
-- SOURCE: change these names to match your linked server and source table
-- e.g. [LINKEDSVR_ABC].[InventoryDB].[dbo].[orders]
--
-- Hard-coded source
-- (Replace these literal names with your real objects)
--
-- Linked server source four-part name
-- NOTE: do not include brackets inside these literals below
-- The script uses them already.

-- Replace values below if needed
-- (they are intentionally hard-coded, not variables)
--
-- Example values used here (update to match your environment):
-- LINKEDSVR_ABC, SrcDatabase, dbo, SrcTable

-- SOURCE object (four-part)
-- [LINKEDSVR_ABC].[SrcDatabase].[dbo].[SrcTable]

-- SINK object
-- [TargetDatabase].[dbo].[TargetTable]

-- PRIMARY KEY column name on both sides
-- Assume a numeric PK column called 'id' (BIGINT). Change if needed.

-- ------------------------------------------------------------------------------
-- If you need to change the hard-coded names, edit the two object names below.
-- ------------------------------------------------------------------------------
DECLARE @srcFourPart NVARCHAR(4000) = N'[LINKEDSVR_ABC].[SrcDatabase].[dbo].[SrcTable]';
DECLARE @sinkFull NVARCHAR(4000)    = N'[TargetDatabase].[dbo].[TargetTable]';
DECLARE @pk_column SYSNAME = N'id';
-- ------------------------------------------------------------------------------

-- Working temp table for keys (assume BIGINT PK for simplicity)
IF OBJECT_ID('tempdb..#Keys') IS NOT NULL DROP TABLE #Keys;
CREATE TABLE #Keys (pk BIGINT PRIMARY KEY);

WHILE 1 = 1
BEGIN
    -- load a batch of keys from source that are within time window and not already in sink
    DELETE FROM #Keys;

    INSERT INTO #Keys (pk)
    SELECT TOP (@BatchSize) src.
        -- use the PK column
        [+] -- placeholder
    FROM ' + @srcFourPart + ' AS src WITH (NOLOCK)
    WHERE src.atime >= @atime AND src.btime < @btime
      AND NOT EXISTS (SELECT 1 FROM ' + @sinkFull + ' sink WHERE sink.' + QUOTENAME('id') + ' = src.' + QUOTENAME('id') + ')
    ORDER BY src.atime, src.' + QUOTENAME('id') + ';

    -- The above dynamic text line is intentionally not executed as-is;
    -- We'll implement the batch-populate using sp_executesql with a built statement because
    -- a four-part name cannot be parameterized directly in a static query when used as object.

    -- Build and execute the actual batch key selector
    DECLARE @selectKeys NVARCHAR(MAX) = N'
    INSERT INTO #Keys (pk)
    SELECT TOP (@BatchSize) src.' + QUOTENAME(@pk_column) + N'
    FROM ' + @srcFourPart + N' AS src WITH (NOLOCK)
    WHERE src.atime >= @atime AND src.btime < @btime
      AND NOT EXISTS (
          SELECT 1 FROM ' + @sinkFull + N' sink WHERE sink.' + QUOTENAME(@pk_column) + N' = src.' + QUOTENAME(@pk_column) + N'
      )
    ORDER BY src.atime, src.' + QUOTENAME(@pk_column) + N';';

    EXEC sp_executesql @selectKeys, N'@BatchSize INT, @atime DATETIME2, @btime DATETIME2', @BatchSize=@BatchSize, @atime=@atime, @btime=@btime;

    IF (SELECT COUNT(1) FROM #Keys) = 0
    BEGIN
        PRINT 'No more rows to migrate (or all matching rows already exist in sink).';
        BREAK;
    END

    -- Insert the rows for this batch from the linked server into the sink
    BEGIN TRAN;
    BEGIN TRY
        DECLARE @insertSql NVARCHAR(MAX) = N'
        INSERT INTO ' + @sinkFull + N'
        SELECT src.*
        FROM ' + @srcFourPart + N' AS src WITH (NOLOCK)
        WHERE src.' + QUOTENAME(@pk_column) + N' IN (SELECT pk FROM #Keys)
          AND NOT EXISTS (
              SELECT 1 FROM ' + @sinkFull + N' sink WHERE sink.' + QUOTENAME(@pk_column) + N' = src.' + QUOTENAME(@pk_column) + N'
          );';

        EXEC sp_executesql @insertSql;
        COMMIT TRAN;
        PRINT CONCAT('Committed batch (', (SELECT COUNT(1) FROM #Keys), ') rows.');
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRAN;
        PRINT CONCAT('Batch failed: ', ERROR_MESSAGE());
        -- optionally: break or CONTINUE to next batch
        BREAK;
    END CATCH
END

DROP TABLE IF EXISTS #Keys;

PRINT 'Simple migration finished.';
