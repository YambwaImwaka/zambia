import requests
import logging
from bs4 import BeautifulSoup
import trafilatura
import re
from datetime import datetime
import time
import json

class BaseCollector:
    """Base class for data collectors"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def collect_data(self, data_type):
        """Override this method in subclasses"""
        raise NotImplementedError

class WorldBankCollector(BaseCollector):
    """Collector for World Bank API data"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.worldbank.org/v2"
        self.country_code = "ZMB"  # Zambia
    
    def collect_data(self, data_type):
        """Collect data from World Bank API"""
        try:
            indicators = self._get_indicators_by_type(data_type)
            
            if not indicators:
                return {
                    'success': False,
                    'error': f'No World Bank indicators found for data type: {data_type}'
                }
            
            all_data = []
            
            for indicator_code, indicator_name in indicators.items():
                try:
                    # Use simpler URL structure
                    url = f"{self.base_url}/country/{self.country_code}/indicator/{indicator_code}"
                    params = {
                        'format': 'json',
                        'date': '2015:2023',
                        'per_page': 50
                    }
                    
                    response = self.session.get(url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if len(data) > 1 and data[1]:
                                for item in data[1]:
                                    if item.get('value') is not None:
                                        all_data.append({
                                            'Indicator': indicator_name,
                                            'Indicator_Code': indicator_code,
                                            'Year': item.get('date', 'N/A'),
                                            'Value': item.get('value', 'N/A'),
                                            'Country': 'Zambia',
                                            'Source': 'World Bank'
                                        })
                        except json.JSONDecodeError:
                            logging.warning(f"Invalid JSON response for {indicator_code}")
                            continue
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logging.warning(f"Failed to fetch indicator {indicator_code}: {str(e)}")
                    continue
            
            # If no API data, create sample structure
            if not all_data:
                all_data = [
                    {
                        'Indicator': f'{data_type.title()} Data',
                        'Value': 'API connection issue - please check World Bank API availability',
                        'Year': datetime.now().year,
                        'Country': 'Zambia',
                        'Source': 'World Bank (Connection Error)'
                    }
                ]
            
            return {
                'success': True,
                'data': all_data,
                'metadata': {
                    'source': 'World Bank',
                    'country': 'Zambia',
                    'records_count': len(all_data)
                }
            }
            
        except Exception as e:
            logging.error(f"World Bank API error: {str(e)}")
            return {
                'success': False,
                'error': f'World Bank data collection failed: {str(e)}'
            }
    
    def _get_indicators_by_type(self, data_type):
        """Map data types to World Bank indicator codes"""
        indicators_map = {
            'population': {
                'SP.POP.TOTL': 'Population, total',
                'SP.POP.GROW': 'Population growth (annual %)',
                'SP.URB.TOTL.IN.ZS': 'Urban population (% of total)'
            },
            'health': {
                'SP.DYN.LE00.IN': 'Life expectancy at birth, total (years)',
                'SH.DYN.MORT': 'Mortality rate, under-5 (per 1,000 live births)',
                'SH.STA.MMRT': 'Maternal mortality ratio'
            },
            'education': {
                'SE.ADT.LITR.ZS': 'Literacy rate, adult total (% of people ages 15 and above)',
                'SE.PRM.NENR': 'School enrollment, primary (% net)',
                'SE.SEC.NENR': 'School enrollment, secondary (% net)'
            },
            'economy': {
                'NY.GDP.MKTP.CD': 'GDP (current US$)',
                'NY.GDP.PCAP.CD': 'GDP per capita (current US$)',
                'NY.GDP.MKTP.KD.ZG': 'GDP growth (annual %)'
            },
            'agriculture': {
                'AG.LND.AGRI.ZS': 'Agricultural land (% of land area)',
                'AG.PRD.CROP.XD': 'Crop production index',
                'AG.LND.ARBL.ZS': 'Arable land (% of land area)'
            },
            'mining': {
                'NY.GDP.MINR.RT.ZS': 'Mineral rents (% of GDP)',
                'TX.VAL.MRCH.CD.WT': 'Merchandise exports (current US$)'
            }
        }
        
        return indicators_map.get(data_type.lower(), {})

class IMFCollector(BaseCollector):
    """Collector for IMF data via web scraping"""
    
    def collect_data(self, data_type):
        """Collect data from IMF country profile"""
        try:
            # Try multiple IMF endpoints
            urls = [
                "https://www.imf.org/en/Countries/ZMB",
                "https://www.imf.org/external/datamapper/profile/ZMB"
            ]
            
            all_data = []
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        # Try BeautifulSoup parsing first
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for economic data tables
                        tables = soup.find_all('table')
                        for table in tables[:3]:  # Check first 3 tables
                            rows = table.find_all('tr')
                            for row in rows:
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 2:
                                    key = cells[0].get_text(strip=True)
                                    value = cells[1].get_text(strip=True)
                                    
                                    if any(keyword in key.lower() for keyword in ['gdp', 'inflation', 'debt', 'growth', 'unemployment']):
                                        all_data.append({
                                            'Indicator': key,
                                            'Value': value,
                                            'Type': data_type.title(),
                                            'Source': 'IMF Website',
                                            'Country': 'Zambia',
                                            'Date': datetime.now().strftime('%Y-%m-%d')
                                        })
                        
                        # Also try trafilatura extraction
                        content = trafilatura.extract(response.text)
                        if content:
                            # Extract numerical data with context
                            patterns = [
                                r'GDP.*?(\d+\.?\d*)\s*(?:billion|million|%)',
                                r'inflation.*?(\d+\.?\d*)\s*(?:percent|%)',
                                r'growth.*?(\d+\.?\d*)\s*(?:percent|%)',
                                r'debt.*?(\d+\.?\d*)\s*(?:percent|%|billion)'
                            ]
                            
                            for i, pattern in enumerate(patterns):
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for j, match in enumerate(matches[:2]):  # Limit matches
                                    indicator_types = ['GDP', 'Inflation', 'Growth', 'Debt']
                                    all_data.append({
                                        'Indicator': f'{indicator_types[i]} Related Metric {j+1}',
                                        'Value': match,
                                        'Type': data_type.title(),
                                        'Source': 'IMF Website',
                                        'Country': 'Zambia',
                                        'Date': datetime.now().strftime('%Y-%m-%d')
                                    })
                        
                        if all_data:
                            break  # Found data, no need to try other URLs
                        
                except Exception as e:
                    logging.warning(f"Failed to scrape {url}: {str(e)}")
                    continue
            
            if not all_data:
                # Provide informative response about data availability
                all_data = [
                    {
                        'Indicator': f'IMF {data_type.title()} Data Status',
                        'Value': 'IMF website access restricted or data format changed',
                        'Type': data_type.title(),
                        'Source': 'IMF Website',
                        'Country': 'Zambia',
                        'Date': datetime.now().strftime('%Y-%m-%d'),
                        'Note': 'Consider accessing IMF data directly from their official statistics portal'
                    }
                ]
            
            return {
                'success': True,
                'data': all_data,
                'metadata': {
                    'source': 'IMF',
                    'data_type': data_type,
                    'records_found': len(all_data)
                }
            }
            
        except Exception as e:
            logging.error(f"IMF scraping error: {str(e)}")
            return {
                'success': False,
                'error': f'IMF data collection failed: {str(e)}'
            }

class USAIDCollector(BaseCollector):
    """Collector for USAID data"""
    
    def collect_data(self, data_type):
        """Collect data from USAID sources"""
        try:
            # Try multiple USAID sources
            urls = [
                "https://www.usaid.gov/zambia",
                "https://www.usaid.gov/zambia/fact-sheets"
            ]
            
            all_data = []
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        content = trafilatura.extract(response.text)
                        
                        if content:
                            # Extract funding and program information
                            funding_patterns = [
                                r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|billion)',
                                r'(\d+(?:,\d{3})*)\s*(?:beneficiaries|people|children|students)',
                                r'(\d+(?:,\d{3})*)\s*(?:programs?|projects?|schools?|clinics?)'
                            ]
                            
                            for pattern in funding_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches[:3]:  # Limit matches
                                    if '$' in pattern:
                                        all_data.append({
                                            'Indicator': 'USAID Funding Amount',
                                            'Value': f'${match}',
                                            'Unit': 'USD',
                                            'Type': 'Development Aid',
                                            'Source': 'USAID Website',
                                            'Country': 'Zambia',
                                            'Date': datetime.now().strftime('%Y-%m-%d')
                                        })
                                    else:
                                        all_data.append({
                                            'Indicator': 'USAID Program Reach',
                                            'Value': match,
                                            'Type': 'Program Data',
                                            'Source': 'USAID Website',
                                            'Country': 'Zambia',
                                            'Date': datetime.now().strftime('%Y-%m-%d')
                                        })
                        
                        if all_data:
                            break
                            
                except Exception as e:
                    logging.warning(f"Failed to scrape {url}: {str(e)}")
                    continue
            
            if not all_data:
                all_data = [
                    {
                        'Indicator': f'USAID {data_type.title()} Programs',
                        'Value': 'USAID website access limited or data structure changed',
                        'Type': data_type.title(),
                        'Source': 'USAID Website',
                        'Country': 'Zambia',
                        'Date': datetime.now().strftime('%Y-%m-%d'),
                        'Note': 'Visit USAID.gov/zambia for current program information'
                    }
                ]
            
            return {
                'success': True,
                'data': all_data,
                'metadata': {
                    'source': 'USAID',
                    'data_type': data_type
                }
            }
            
        except Exception as e:
            logging.error(f"USAID scraping error: {str(e)}")
            return {
                'success': False,
                'error': f'USAID data collection failed: {str(e)}'
            }

class UNCollector(BaseCollector):
    """Collector for UN data"""
    
    def collect_data(self, data_type):
        """Collect data from UN sources"""
        try:
            # Try UN Data portal and other UN sources
            urls = [
                "https://data.un.org/_layouts/15/UNStats/Country.aspx?cid=894",  # Zambia country code
                "https://unstats.un.org/unsd/demographic-social/products/vitstats/serartic2.pdf"
            ]
            
            all_data = []
            
            # Try UN Data portal first
            try:
                response = self.session.get(urls[0], timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for statistical tables
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                indicator = cells[0].get_text(strip=True)
                                value = cells[1].get_text(strip=True)
                                
                                if indicator and value and len(indicator) > 3:
                                    all_data.append({
                                        'Indicator': indicator,
                                        'Value': value,
                                        'Type': data_type.title(),
                                        'Source': 'UN Data Portal',
                                        'Country': 'Zambia',
                                        'Date': datetime.now().strftime('%Y-%m-%d')
                                    })
                    
                    if len(all_data) > 10:  # If we got good data, stop here
                        all_data = all_data[:10]  # Limit results
                    
            except Exception as e:
                logging.warning(f"UN Data portal access failed: {str(e)}")
            
            # If no data from main portal, try alternative approach
            if not all_data:
                # Create informative response about UN data
                un_indicators = {
                    'population': ['Total Population', 'Urban Population %', 'Population Density'],
                    'health': ['Life Expectancy', 'Infant Mortality Rate', 'Maternal Mortality'],
                    'education': ['Literacy Rate', 'Primary School Enrollment', 'Secondary School Enrollment'],
                    'economy': ['GDP per Capita', 'Human Development Index', 'Poverty Rate'],
                    'agriculture': ['Agricultural Employment %', 'Food Security Index', 'Rural Population %'],
                    'mining': ['Natural Resource Rents', 'Export Diversification', 'Mining Employment']
                }
                
                indicators = un_indicators.get(data_type.lower(), ['General Statistics'])
                
                for indicator in indicators:
                    all_data.append({
                        'Indicator': indicator,
                        'Value': 'UN data portal access restricted - visit data.un.org for latest statistics',
                        'Type': data_type.title(),
                        'Source': 'UN Data Portal',
                        'Country': 'Zambia',
                        'Date': datetime.now().strftime('%Y-%m-%d'),
                        'Note': 'Direct access to UN statistical databases recommended'
                    })
            
            return {
                'success': True,
                'data': all_data,
                'metadata': {
                    'source': 'UN Agencies',
                    'data_type': data_type
                }
            }
            
        except Exception as e:
            logging.error(f"UN data collection error: {str(e)}")
            return {
                'success': False,
                'error': f'UN data collection failed: {str(e)}'
            }