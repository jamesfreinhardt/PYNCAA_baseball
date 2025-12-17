# NCAA Baseball School Finder - Python/Dash Version

This is a Python rewrite of the NCAA Baseball School Finder application, originally built in R Shiny.

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The app will start on http://localhost:8050

## Key Differences from R Version

### Framework
- **R Shiny** → **Plotly Dash**
- Reactive programming via callbacks instead of reactive expressions

### Libraries
- `dplyr` → `pandas`
- `leaflet` → `dash-leaflet`
- `plotly` (same in both)
- `geosphere` → `geopy`

### Features Implemented
✅ Interactive map with school markers
✅ All filter panels (Location, Team, Demographics, Academic)
✅ Climate filtering with monthly data
✅ School counter
✅ Reset all filters button
✅ Multiple tabs (Map, Filtered List, Saved List, Roster Metrics)

### Features To Be Added
- [ ] Saved schools functionality (add/remove)
- [ ] Data tables for filtered and saved lists
- [ ] Roster metrics charts (class distribution, state recruiting, history)
- [ ] Distance calculation from home zip
- [ ] Map clustering and popups with "Add to Saved" button
- [ ] View extent filtering
- [ ] Coach and team metrics

## File Structure

```
NCAABaseball/
├── app.py                              # Main Dash application
├── requirements.txt                     # Python dependencies
├── input_filtered.csv                   # Main school data
├── climate_data_processed.csv           # Climate data (wide format)
├── climate_data_monthly_long.csv        # Climate data (long format)
├── combined_ncaa_rosters_filtered.csv   # Roster data
└── README_PYTHON.md                     # This file
```

## Next Steps

1. **Test the basic version**: Run `python app.py` and verify filters work
2. **Add data tables**: Implement DataTable components for filtered/saved lists
3. **Add saved schools**: Implement add/remove/clear functionality
4. **Add roster charts**: Port the Plotly charts from R version
5. **Enhance map**: Better popups, clustering, and interactions
6. **Deploy**: Consider Heroku, AWS, or other cloud platforms

## Deployment Options

- **Heroku**: Free tier available, easy deployment
- **AWS Elastic Beanstalk**: More control, scalable
- **Google Cloud Run**: Containerized, pay-per-use
- **Dash Enterprise**: Commercial option with more features

## Performance Notes

- Python version should handle 100+ concurrent users
- Can add caching with `@cache.memoize()` for better performance
- Consider using Dask for larger datasets
