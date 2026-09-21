

--select * from staging_download_shipMILS
----1--Format the MILSTRIPs using below examples
/*
--examples formatted (A2s do not require prices after the "SMSAA")
A2ASTZ08405015308058  EA00140SL470151000BAJ SC0140MKK      03103  SMSAA  0001657
A2ASTZ08405015308058  EA00340SL470151000BCG SC1143MKK      03103  SMSAA  0001657
A2ASTZ08405015308034  EA00050SL470151000BDC SC1143MKK      03103  SMSAA
A5ASTZS8405012795607  EA00084SL470150160BYS SC1143MKK   RDO03999  SMSAA  0016489
A5ESTZS7210001195335  EA01500SC010050162200 SC0101M00   HSI06035  SMSAA  0000465


--the totally not garbage version from DLA personnel


A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA      
A2ASTZ08405016819460  EA00420SL470162240DDL SC0141MKK      15     SMSAA      
A2ASTZ08405016819468  EA00300SL470162240DDQ SC0141MKK      15     SMSAA      
A2ASTZ08405016819531  EA00140SL470162240DDT SC0141MKK      15     SMSAA      



A5ASTZS7210014980279  EA00007N6278661680738 N50408JMQ 9BMP903999
--original from 2026-06-18

select * from itemmaster where item =
'7210014980306'

select * from shipmaster
where shiptododaac = 'M34000'
order by datecreated desc





select * from download_ship940
where erp_order = 'V216876209S111'

select * from shipmaster
where erp_order = 'V216876209S111'


A5ASTZS7210014980306  EA00001V216876209S111 YNSS01ASE 9BEP502999  SMSAA

*/

----2. Place the multiple formatted MILSTRIPS in the below script and Run script
-------Note: VERY IMPORTANT - Any A5E MILSTRIPs need to be batch group entered seperately from non-A5E or differing customers
-------Non-A5E are ok to put in all at once

-----THIS IS WHERE YOU PUT IN MULTIPLE MILS at once (below)
-----THIS IS WHERE YOU PUT IN MULTIPLE MILS at once (below)

INSERT INTO staging_download_shipMILS (mils)
VALUES

 ('A2ASTZ08405016819440  EA00520SL470162240DCV SC0141MKK      15     SMSAA')     
,('A2ASTZ08405016819460  EA00420SL470162240DDL SC0141MKK      15     SMSAA')     
,('A2ASTZ08405016819468  EA00300SL470162240DDQ SC0141MKK      15     SMSAA')     
,('A2ASTZ08405016819531  EA00140SL470162240DDT SC0141MKK      15     SMSAA')     

select * 
from staging_download_shipMILS



-- ('A2ASTZ08405015159002  EA00060SL470162100DRN SC1143MKK      03        AA  SMS')    
--,('A2ASTZ08405015159010  EA00060SL470162100DRQ SC1143MKK      03        AA  SMS')    
--,('A2ASTZ08405015159012  EA00060SL470162100EYP SC1143MKK      03        AA  SMS')    
--,('A2ASTZ08405015158972  EA00360SL470162100EZU SC1143MKK      03        AA  SMS')    
--,('A2ASTZ08405015158977  EA00120SL470162100FAC SC1143MKK      03        AA  SMS')    


/*
 ('A51STZS8470016751195  EA00050N611086105EM19 N67641JDA 9B9AL019992LSMSAA')
,('A5ASTZS8470016751195  EA00040V454723048TM10 YARMO ABE   LK5029992LSMSAA')
,('A5ASTZS8470016751195  EA00015N647105065E812       ADVE9BXY901080  SMSAA')
*/

---THIS IS WHERE YOU PUT IN MULTIPLE MILS in batch (above)
---THIS IS WHERE YOU PUT IN MULTIPLE MILS in batch (above)


--3. Run the script below - AGAIN - if it's A5E, then you must enter the address in the section below
 

DECLARE @rightNow datetime
SET @rightnow = CAST(Datetrunc(MILLISECOND, getdate() AT TIME ZONE 'UTC' AT TIME ZONE 'Central Standard Time') as datetime)

DECLARE   @mils nvarchar(80), @nsn nchar(13), @listPrice nvarchar(12) ,@milsPrice nvarchar(7), @dodaac nchar(6), @docNr nvarchar(14), @first6 nchar(6), @pg nchar(2) 
		, @SHIPTOCITY nvarchar(20), @SHIPTOLINE1 nvarchar(35), @SHIPTOLINE2 nvarchar(35), @SHIPTOLINE3 nvarchar(35), @SHIPTOLINE4 nvarchar(35)
		, @SHIPTOSTATE nvarchar(2), @SHIPTOCOUNTRY nvarchar(2), @SHIPTOZIP nvarchar(10), @PHONE nvarchar(15), @SHIPTOCAREOF nvarchar(20), @SUPPLYCENTERRIC nchar(3)
		, @INSTRUCTIONS nvarchar(20)

WHILE	(
		SELECT	COUNT(*)
		FROM	staging_download_shipMILS
		WHERE	milsStatus IS NULL
		) > 0

		BEGIN
			SET @mils	= (SELECT TOP 1 mils from staging_download_shipMILS WHERE milsStatus IS NULL)
			SET @nsn	= SUBSTRING(@mils, 8,13)
			SET @dodaac = SUBSTRING(@mils,45, 6)
			SET @docNr	= SUBSTRING(@mils,30, 15)
			SET @pg =	CASE
							WHEN SUBSTRING(@mils,60,2) BETWEEN '01' and '03' THEN '01'
							WHEN SUBSTRING(@mils,60,2) BETWEEN '04' and '08' THEN '02'
							WHEN SUBSTRING(@mils,60,2) BETWEEN '09' and '15' THEN '03'
							ELSE '03'
						END
			SET @first6		= SUBSTRING(@mils,30,6)
			SET @dodaac		= CASE WHEN SUBSTRING(@mils,51,1) < 'J' THEN @first6 ELSE SUBSTRING(@mils,45, 6) END
			SET	@listPrice	= 
				(
				SELECT	CASE 
							WHEN ISNUMERIC(@milsPrice) = 1 THEN CAST(@milsPrice as money) * .01
							--WHEN @milsPrice IS NULL THEN (Select LIST_PRICE from ItemMaster where item = @nsn)
							ELSE (Select LIST_PRICE from ItemMaster where item = @nsn)
						END
				)
			SET @SUPPLYCENTERRIC = 
				CASE 
					WHEN SUBSTRING(@mils, 1,2) = 'A2' THEN SUBSTRING(@mils,74,3) 
					WHEN SUBSTRING(@mils, 1,2) = 'A5' THEN SUBSTRING(@mils,67,3)  
				END

			--Leave NULL in these unless there is an A5E exception address, then leave all NOT NULL or ''
			----WORK STOPPAGE USS IDAHO HULL SSN 799
			----N271625175C468 NSN 7210014980292 Qty 12 
			--SHIP TO: (N27162-5175-C468) PCU IDAHO SSN 799
			--Eagle Park Electric Boat Corporation
			--25 Norwich Westerly Rd.
			--Stonington, CT 
			--POC:  RICK MYSHKA
			--PHONE: 860-433-4848

			SET @SHIPTOCITY		= NULL	--*/ UPPER('Aberdeen Proving Ground')
			SET @SHIPTOLINE1	= NULL	--*/ UPPER('6850 Lanyard Road')	
			SET @SHIPTOLINE2	= NULL	--*/ UPPER('Building 608')	
			SET @SHIPTOLINE3	= NULL	--*/ UPPER('Soldier Survivability Branch')	
			SET @SHIPTOLINE4	= NULL	--*/ UPPER('')	
			SET @SHIPTOSTATE	= NULL	--*/ UPPER('MD ')	
			SET @SHIPTOCOUNTRY	= NULL	--*/ UPPER('US')	
			SET @SHIPTOZIP		= NULL	--*/ UPPER('21005-5059')
			SET @PHONE			= NULL	--*/ UPPER('860-433-4848')
			SET @SHIPTOCAREOF	= NULL	--*/ UPPER('Christopher DAmario')
			SET @INSTRUCTIONS	= NULL	--*/ UPPER('Soldier Survivability Branch' )
			
			--SELECT @mils

			INSERT INTO download_ship940--_mils
					(BornOnDate
					,InterfaceID
					,[dic]
					,[ADVICECODE]
					,[BILLTODODAAC]
					,[COND_CD]
					--[DELIVERADD stuff later]
					,[DIST_CD]
					,DATECREATED
					,[FUND_CD]
					,[MEDIA_STAT_CD]
					,[NSN]
					,[OP_CD]
					,[ORDERQTY],[PRIORITYCODE],[PROJECTCODE],[RDD],[RIC],[REQUISITION],[SIGNAL_CD],[STD_UP],[SUPP_ADDR]
					,[SHIPTOCITY],[SHIPTODODAAC],[SHIPTOLINE1],[SHIPTOLINE2],[SHIPTOLINE3],[SHIPTOLINE4],[SHIPTOSTATE],[SHIPTOCOUNTRY],[SHIPTOZIP]
					,[STATUSTODODAAC],[SUFFIX],[SUPPLYCENTERRIC],[UI]
					,[ERP_ORDER]
					,OrderSourceType
					,calendarDate3PL
					,Note3PL
					)

			SELECT	--i.item, d.erp_order,
					 t.BornOnDate,t.InterfaceID,t.DIC,t.ADVICECODE,t.BILLTODODAAC,t.COND_CD,t.DIST_CD,t.DATECREATED,t.FUND_CD,t.MEDIA_STAT_CD		
					,t.NSN,t.OP_CD,t.ORDERQTY,t.PRIORITYCODE,t.PROJECTCODE,t.RDD,t.RIC,t.REQUISITION,t.SIGNAL_CD,t.STD_UP
					,t.SUPP_ADDR,t.SHIPTOCITY,t.SHIPTODODAAC,t.SHIPTOLINE1,t.SHIPTOLINE2,t.SHIPTOLINE3,t.SHIPTOLINE4,t.SHIPTOSTATE,t.SHIPTOCOUNTRY,t.SHIPTOZIP
					,t.STATUSTODODAAC,t.SUFFIX,t.SUPPLYCENTERRIC
					,i.UM1 AS UI
					,t.ERP_ORDER,t.OrderSourceType,t.calendarDate3PL,t.Note3PL
			FROM
				(
				SELECT	TOP 1	
						 BornOnDate		= @rightNow
						, InterfaceID = NULL
						--MILS attributes follow
						, DIC				= SUBSTRING(@mils, 1, 3)		
						, ADVICECODE		= SUBSTRING(@mils, 65, 2)		
						, BILLTODODAAC		= CASE WHEN SUBSTRING(@mils,1,2) = 'A5' THEN SUBSTRING(@mils, 45, 6) ELSE NULL END --check on A5J later for this
						, COND_CD			= SUBSTRING(@mils, 71, 1)
						--, DEMANDCODE		= NULL (for now)
						/*Put in "DeliveryAdd exception addresses here later*/
						, DIST_CD			= SUBSTRING(@mils, 54, 3)
						, DATECREATED		= @rightNow	
						, FUND_CD			= SUBSTRING(@mils, 52, 2)		
						, MEDIA_STAT_CD		= SUBSTRING(@mils, 7, 1)       
						, NSN				= SUBSTRING(@mils, 8, 13)
						, OP_CD				= SUBSTRING(@mils, 70, 1)
						, ORDERQTY			= CAST(SUBSTRING(@mils, 25, 5)AS INT)
						, PRIORITYCODE		= SUBSTRING(@mils, 60, 2)
						, PROJECTCODE		= SUBSTRING(@mils, 57, 3)
						, RDD				= SUBSTRING(@mils, 62, 3)
						, RIC				= SUBSTRING(@mils, 4, 3)
						, REQUISITION		= SUBSTRING(@mils, 30, 14)
						, SIGNAL_CD			= SUBSTRING(@mils, 51, 1)
						, STD_UP			= @listPrice
						, SUPP_ADDR			= SUBSTRING(@mils, 45, 6)
						, SHIPTOCITY		= ISNULL(@SHIPTOCITY ,d.City)
						, SHIPTODODAAC		= @dodaac
						, SHIPTOLINE1		= ISNULL(@SHIPTOLINE1 ,d.Add1)
						, SHIPTOLINE2		= ISNULL(@SHIPTOLINE2 ,d.Add2)
						, SHIPTOLINE3		= ISNULL(@SHIPTOLINE3 ,d.Add3)
						, SHIPTOLINE4		= ISNULL(@SHIPTOLINE4 ,d.Add4)
						, SHIPTOSTATE		= ISNULL(@SHIPTOSTATE ,d.State	)	
						, SHIPTOCOUNTRY		= ISNULL(@SHIPTOCOUNTRY ,d.CntryCd)
						, SHIPTOZIP			= ISNULL(@SHIPTOZIP ,d.Zip)
						--skip STATUS (leave Null)
						, STATUSTODODAAC	= @dodaac
						, SUFFIX			= CASE WHEN SUBSTRING(@mils, 44, 1) = ' ' THEN NULL ELSE SUBSTRING(@mils, 44, 1) END
						, SUPPLYCENTERRIC	= 'SMS' --CASE WHEN @SUPPLYCENTERRIC IS NULL OR @SUPPLYCENTERRIC != 'SMS' THEN 'SMS' END 
						, UI				= SUBSTRING(@mils, 23, 2)

						--3pl internal stuff
						, ERP_ORDER			= RTRIM(SUBSTRING(@mils, 30, 14)+ ISNULL(SUBSTRING(@mils, 44, 1),''))
						, OrderSourceType	= 2 --(2 means "MILSTRIP")
						, calendarDate3PL	= DATETRUNC(dd,@rightNow)
						, Note3PL			= CONVERT(char(8),@rightnow,112) +'_milstrip'
				FROM	dbo.cfg_dodaac_active d 
				WHERE	dodaac = @dodaac
				AND		@docNr NOT IN (SELECT RTRIM(ERP_ORDER) from download_ship940 WHERE DIC = SUBSTRING(@mils, 1, 3) and SUBSTRING(DIC,1,2) IN ('A2','A5'))
				) t LEFT OUTER JOIN ItemMaster i on t.nsn = i.item
					LEFT OUTER JOIN download_ship940/*_mils*/ d on t.ERP_ORDER = d.ERP_ORDER
			WHERE	
					d.ERP_ORDER IS NULL --Must be a new order
			AND		i.ITEM IS NOT NULL	--Item must pre-exist in 3PL SCALE database

			UPDATE staging_download_shipMILS SET milsStatus = 'SENT' WHERE mils = @mils

			--SELECT	COUNT(*)
			--FROM	staging_download_shipMILS
			--WHERE	milsStatus IS NULL


			IF
				(
				SELECT	COUNT(*)
				FROM	staging_download_shipMILS
				WHERE	milsStatus IS NULL
				) = 0
				BREAK
			ELSE 
				CONTINUE
		END

	select * 
	from download_ship940 where erp_order in
	(
	 'SL470162240DCV'
	,'SL470162240DDL'
	,'SL470162240DDQ'
	,'SL470162240DDT'
	)