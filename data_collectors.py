import requests
import logging
from bs4 import BeautifulSoup
import trafilatura
import re
from datetime import datetime
import time

class BaseCollector:
    """Base class for data collectors"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
            
            for indicator in indicators:
                try:
                    url = f"{self.base_url}/countries/{self.country_code}/indicators/{indicator}"
                    params = {
                        'format': 'json',
                        'date': '2010:2024',  # Last 15 years
                        'per_page': 100
                    }
                    
                    response = self.session.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if len(data) > 1 and data[1]:  # World Bank returns [metadata, data]
                        for item in data[1]:
                            if item['value'] is not None:
                                all_data.append({
                                    'Indicator': item['indicator']['value'],
                                    'Indicator_Code': item['indicator']['id'],
                                    'Year': item['date'],
                                    'Value': item['value'],
                                    'Country': item['country']['value'],
                                    'Source': 'World Bank'
                                })
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logging.warning(f"Failed to fetch indicator {indicator}: {str(e)}")
                    continue
            
            if not all_data:
                return {
                    'success': False,
                    'error': 'No data retrieved from World Bank API'
                }
            
            return {
                'success': True,
                'data': all_data,
                'metadata': {
                    'source': 'World Bank',
                    'country': 'Zambia',
                    'indicators_count': len(indicators),
                    'records_count': len(all_data)
                }
            }
            
        except Exception as e:
            logging.error(f"World Bank API error: {str(e)}")
            return {
                'success': False,
                'error': f'World Bank API error: {str(e)}'
            }
    
    def _get_indicators_by_type(self, data_type):
        """Map data types to World Bank indicator codes"""
        indicators_map = {
            'population': [
                'SP.POP.TOTL',  # Population, total
                'SP.POP.GROW',  # Population growth (annual %)
                'SP.URB.TOTL.IN.ZS',  # Urban population (% of total)
                'SP.RUR.TOTL.ZS'  # Rural population (% of total)
            ],
            'health': [
                'SP.DYN.LE00.IN',  # Life expectancy at birth
                'SH.DYN.MORT',  # Mortality rate, under-5
                'SH.STA.MMRT',  # Maternal mortality ratio
                'SH.IMM.MEAS'  # Immunization, measles
            ],
            'education': [
                'SE.ADT.LITR.ZS',  # Literacy rate, adult total
                'SE.PRM.NENR',  # School enrollment, primary
                'SE.SEC.NENR',  # School enrollment, secondary
                'SE.TER.ENRR'  # School enrollment, tertiary
            ],
            'economy': [
                'NY.GDP.MKTP.CD',  # GDP (current US$)
                'NY.GDP.PCAP.CD',  # GDP per capita (current US$)
                'NY.GDP.MKTP.KD.ZG',  # GDP growth (annual %)
                'FP.CPI.TOTL.ZG'  # Inflation, consumer prices
            ],
            'agriculture': [
                'AG.LND.AGRI.ZS',  # Agricultural land (% of land area)
                'AG.PRD.CROP.XD',  # Crop production index
                'AG.LND.ARBL.ZS',  # Arable land (% of land area)
                'AG.YLD.CREL.KG'  # Cereal yield (kg per hectare)
            ],
            'mining': [
                'NY.GDP.MINR.RT.ZS',  # Mineral rents (% of GDP)
                'TX.VAL.MRCH.CD.WT',  # Merchandise exports (current US$)
                'EG.USE.COMM.CL.ZS'  # Alternative and nuclear energy
            ]
        }
        
        return indicators_map.get(data_type.lower(), [])

class IMFCollector(BaseCollector):
    """Collector for IMF data via web scraping"""
    
    def collect_data(self, data_type):
        """Collect data from IMF website"""
        try:
            url = "https://www.imf.org/en/Countries/ZMB"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract content using trafilatura
            content = trafilatura.extract(response.text)
            
            if not content:
                return {
                    'success': False,
                    'error': 'Failed to extract content from IMF website'
                }
            
            # Parse content for relevant data
            data = self._parse_imf_content(content, data_type)
            
            if not data:
                return {
                    'success': False,
                    'error': f'No relevant {data_type} data found on IMF website'
                }
            
            return {
                'success': True,
                'data': data,
                'metadata': {
                    'source': 'IMF',
                    'url': url,
                    'data_type': data_type
                }
            }
            
        except Exception as e:
            logging.error(f"IMF scraping error: {str(e)}")
            return {
                'success': False,
                'error': f'IMF website scraping failed: {str(e)}'
            }
    
    def _parse_imf_content(self, content, data_type):
        """Parse IMF content for specific data types"""
        data = []
        
        # Look for economic indicators
        if data_type.lower() == 'economy':
            # Extract GDP, inflation, fiscal data
            gdp_matches = re.findall(r'GDP.*?(\d+\.?\d*)\s*(?:percent|%|billion|million)', content, re.IGNORECASE)
            inflation_matches = re.findall(r'inflation.*?(\d+\.?\d*)\s*(?:percent|%)', content, re.IGNORECASE)
            
            for i, gdp in enumerate(gdp_matches[:3]):  # Limit to first 3 matches
                data.append({
                    'Indicator': f'GDP Related Metric {i+1}',
                    'Value': gdp,
                    'Type': 'Economic',
                    'Source': 'IMF Website',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
            
            for i, inflation in enumerate(inflation_matches[:3]):
                data.append({
                    'Indicator': f'Inflation Related Metric {i+1}',
                    'Value': inflation,
                    'Type': 'Economic',
                    'Source': 'IMF Website',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
        
        # General data extraction for other types
        else:
            # Extract any numerical data with percentages or currency
            numeric_matches = re.findall(r'(\d+\.?\d*)\s*(?:percent|%|billion|million|USD|\$)', content)
            
            for i, value in enumerate(numeric_matches[:10]):  # Limit results
                data.append({
                    'Indicator': f'{data_type.title()} Metric {i+1}',
                    'Value': value,
                    'Type': data_type.title(),
                    'Source': 'IMF Website',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
        
        return data

class USAIDCollector(BaseCollector):
    """Collector for USAID data via web scraping"""
    
    def collect_data(self, data_type):
        """Collect data from USAID website"""
        try:
            url = "https://www.usaid.gov/zambia"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            content = trafilatura.extract(response.text)
            
            if not content:
                return {
                    'success': False,
                    'error': 'Failed to extract content from USAID website'
                }
            
            data = self._parse_usaid_content(content, data_type)
            
            if not data:
                return {
                    'success': False,
                    'error': f'No relevant {data_type} data found on USAID website'
                }
            
            return {
                'success': True,
                'data': data,
                'metadata': {
                    'source': 'USAID',
                    'url': url,
                    'data_type': data_type
                }
            }
            
        except Exception as e:
            logging.error(f"USAID scraping error: {str(e)}")
            return {
                'success': False,
                'error': f'USAID website scraping failed: {str(e)}'
            }
    
    def _parse_usaid_content(self, content, data_type):
        """Parse USAID content for specific data types"""
        data = []
        
        # Look for funding and program data
        funding_matches = re.findall(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|billion)', content, re.IGNORECASE)
        program_matches = re.findall(r'(\d+)\s*(?:programs?|projects?|beneficiaries)', content, re.IGNORECASE)
        
        for i, amount in enumerate(funding_matches[:5]):
            data.append({
                'Indicator': f'USAID Funding Amount {i+1}',
                'Value': amount,
                'Unit': 'USD',
                'Type': 'Development Aid',
                'Source': 'USAID Website',
                'Date': datetime.now().strftime('%Y-%m-%d')
            })
        
        for i, count in enumerate(program_matches[:5]):
            data.append({
                'Indicator': f'Program/Beneficiary Count {i+1}',
                'Value': count,
                'Type': 'Program Data',
                'Source': 'USAID Website',
                'Date': datetime.now().strftime('%Y-%m-%d')
            })
        
        # Add data type specific information
        if data_type.lower() in ['health', 'education', 'agriculture']:
            # Look for sector-specific mentions
            sector_matches = re.findall(rf'{data_type}.*?(\d+(?:,\d{{3}})*)', content, re.IGNORECASE)
            for i, value in enumerate(sector_matches[:3]):
                data.append({
                    'Indicator': f'{data_type.title()} Related Metric {i+1}',
                    'Value': value.replace(',', ''),
                    'Type': data_type.title(),
                    'Source': 'USAID Website',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
        
        return data

class UNCollector(BaseCollector):
    """Collector for UN data via web scraping"""
    
    def collect_data(self, data_type):
        """Collect data from UN websites"""
        try:
            # Try multiple UN sources
            urls = [
                "https://data.un.org/en/iso/zm.html",
                "https://www.unicef.org/zambia/"
            ]
            
            all_data = []
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=30)
                    response.raise_for_status()
                    
                    content = trafilatura.extract(response.text)
                    
                    if content:
                        data = self._parse_un_content(content, data_type, url)
                        all_data.extend(data)
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logging.warning(f"Failed to scrape {url}: {str(e)}")
                    continue
            
            if not all_data:
                return {
                    'success': False,
                    'error': 'No data found from UN websites'
                }
            
            return {
                'success': True,
                'data': all_data,
                'metadata': {
                    'source': 'UN Agencies',
                    'urls_scraped': len(urls),
                    'data_type': data_type
                }
            }
            
        except Exception as e:
            logging.error(f"UN scraping error: {str(e)}")
            return {
                'success': False,
                'error': f'UN website scraping failed: {str(e)}'
            }
    
    def _parse_un_content(self, content, data_type, source_url):
        """Parse UN content for specific data types"""
        data = []
        
        # Extract development indicators
        if 'unicef' in source_url.lower():
            # UNICEF specific parsing
            child_matches = re.findall(r'(\d+(?:,\d{3})*)\s*(?:children|child)', content, re.IGNORECASE)
            mortality_matches = re.findall(r'mortality.*?(\d+(?:\.\d+)?)', content, re.IGNORECASE)
            
            for i, count in enumerate(child_matches[:3]):
                data.append({
                    'Indicator': f'Children Related Metric {i+1}',
                    'Value': count.replace(',', ''),
                    'Type': 'Child Welfare',
                    'Source': 'UNICEF',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
            
            for i, rate in enumerate(mortality_matches[:3]):
                data.append({
                    'Indicator': f'Mortality Rate {i+1}',
                    'Value': rate,
                    'Type': 'Health',
                    'Source': 'UNICEF',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
        
        else:
            # General UN data parsing
            percentage_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:percent|%)', content)
            large_numbers = re.findall(r'(\d+(?:,\d{3})+)', content)
            
            for i, percentage in enumerate(percentage_matches[:5]):
                data.append({
                    'Indicator': f'Percentage Indicator {i+1}',
                    'Value': percentage,
                    'Unit': 'Percent',
                    'Type': data_type.title(),
                    'Source': 'UN Data',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
            
            for i, number in enumerate(large_numbers[:5]):
                data.append({
                    'Indicator': f'Count Indicator {i+1}',
                    'Value': number.replace(',', ''),
                    'Type': data_type.title(),
                    'Source': 'UN Data',
                    'Date': datetime.now().strftime('%Y-%m-%d')
                })
        
        return data
