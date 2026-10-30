# R macro for interval calculation
# Calculates days between a start date and an end date based on SDTM rules
# (If end date is on or after start date: end - start + 1)
# (If end date is before start date: end - start)

calculate_interval <- function(start_date, end_date) {
  start <- as.Date(start_date)
  end <- as.Date(end_date)
  
  diff_days <- as.numeric(end - start)
  
  interval <- ifelse(!is.na(diff_days) & diff_days >= 0, diff_days + 1, diff_days)
  
  return(interval)
}
