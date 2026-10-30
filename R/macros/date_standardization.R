# R macro for date standardization
# Converts various date formats into standard ISO 8601 (YYYY-MM-DD)

standardize_date <- function(date_vec, format_in = "%d/%m/%Y") {
  # If already in ISO, as.Date might still parse it if format_in matches,
  # but it's safer to try parsing and return character in YYYY-MM-DD.
  parsed_dates <- as.Date(date_vec, format = format_in)
  
  # For values that failed to parse (NA), we could try another format or leave as NA
  
  return(as.character(parsed_dates))
}
