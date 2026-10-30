# Pipeline in R to read dummy datasets, apply macros and export

# Source the macros
source("D:/Development/SAS/R/macros/date_standardization.R")
source("D:/Development/SAS/R/macros/calculate_interval.R")
source("D:/Development/SAS/R/macros/derive_epoch.R")

# 1. Read source data
dm_raw <- read.csv("D:/Development/SAS/data/raw/dm.csv", stringsAsFactors = FALSE)
ta_raw <- read.csv("D:/Development/SAS/data/raw/ta.csv", stringsAsFactors = FALSE)

# 2. Date Standardization
# Let's assume BRTHDTC came as DD/MM/YYYY and we want to standardize it.
# (In our dummy data it's already YYYY-MM-DD but this demonstrates the macro)
dm_raw$BRTHDTC_STD <- standardize_date(dm_raw$BRTHDTC, format_in = "%Y-%m-%d")

# 3. Calculation of interval
# Let's calculate the study day for RFENDTC based on RFSTDTC
dm_raw$RFENDY <- calculate_interval(dm_raw$RFSTDTC, dm_raw$RFENDTC)

# 4. Derivation of EPOCH from T domains / DM dataset
dm_with_epoch <- derive_epoch(dm_raw, ta_raw)

# 5. Exporting to SDTM/ADAM
write.csv(dm_raw, "D:/Development/SAS/data/sdtm/DM.csv", row.names = FALSE)
write.csv(dm_with_epoch, "D:/Development/SAS/data/adam/ADSL_EPOCH.csv", row.names = FALSE)

cat("Pipeline executed successfully. Data exported to data/sdtm/ and data/adam/.\n")
