import pandas as pd
import re
import os
import json
from datetime import datetime
from typing import Tuple, Dict, List
import numpy as np

class GSTMatcher:
    def __init__(self, config_path: str = "config.json"):
        self.config = self.load_config(config_path)
        self.company_columns = list(self.config['columns']['company'].values())
        self.portal_columns = list(self.config['columns']['portal'].values())
    
    def load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        return {
            "columns": {
                "company": {
                    "gstin": "GSTIN of supplier",
                    "party_name": "Party Name",
                    "accounting_doc": "Accounting Document No",
                    "invoice_no": "Invoice No",
                    "invoice_date": "Invoice Date",
                    "cgst": "CGST Amount",
                    "sgst": "SGST Amount",
                    "igst": "IGST Amount"
                },
                "portal": {
                    "gstin": "GSTIN of supplier",
                    "invoice_no": "Invoice number",
                    "invoice_date": "Invoice Date",
                    "cgst": "Central Tax(₹)",
                    "sgst": "State/UT Tax(₹)",
                    "igst": "Integrated Tax(₹)"
                }
            },
            "date_formats": {
                "company": "%d-%m-%Y",
                "portal": "%d/%m/%Y"
            }
        }
        
    def load_data(self, company_path: str, portal_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        try:
            company_df = pd.read_excel(company_path)[self.company_columns]
            portal_df = pd.read_excel(portal_path)[self.portal_columns]
            
            company_df["Invoice Date"] = pd.to_datetime(company_df["Invoice Date"], format=self.config['date_formats']['company'])
            portal_df["Invoice Date"] = pd.to_datetime(portal_df["Invoice Date"], format=self.config['date_formats']['portal'])
            
            company_df['Total'] = company_df['CGST Amount'] + company_df['SGST Amount'] + company_df['IGST Amount']
            portal_df['Total'] = portal_df['Central Tax(₹)'] + portal_df['State/UT Tax(₹)'] + portal_df['Integrated Tax(₹)']
            
            return company_df, portal_df
            
        except KeyError as e:
            raise ValueError(f"Column not found: {e}")
        except Exception as e:
            raise ValueError(f"Error loading data: {e}")
    
    def clean_invoice(self, invoice: str) -> str:
        return re.sub('[^0-9a-zA-Z]+', '', str(invoice))
    
    def match_invoices(self, company_df: pd.DataFrame, portal_df: pd.DataFrame, buffer_size: float = 0) -> Tuple[List[Dict], List[Dict]]:
        company_df['Clean_Invoice'] = company_df['Invoice No'].apply(self.clean_invoice)
        portal_df['Clean_Invoice'] = portal_df['Invoice number'].apply(self.clean_invoice)
        
        company_df['Date_Str'] = company_df['Invoice Date'].dt.strftime('%d-%m-%Y')
        
        exact_matches = company_df.merge(
            portal_df,
            left_on=['GSTIN of supplier', 'Clean_Invoice'],
            right_on=['GSTIN of supplier', 'Clean_Invoice'],
            how='inner',
            suffixes=('_company', '_portal')
        )
        
        matched_records = []
        for _, row in exact_matches.iterrows():
            matched_records.append({
                'GSTIN': row['GSTIN of supplier'],
                'Party Name': row['Party Name'],
                'Accounting Document No': row['Accounting Document No'],
                'Invoice No': row['Invoice No'],
                'Invoice Date': row['Date_Str'],
                'Firm Total': row['Total_company'],
                'Portal Total': row['Total_portal'],
                'Difference': row['Total_portal'] - row['Total_company'],
                'Match Status': 'Exact',
                'Portal Match': row['Invoice number']
            })
        
        matched_invoices = set(exact_matches['Invoice No'].values)
        unmatched_company = company_df[~company_df['Invoice No'].isin(matched_invoices)].copy()
        
        close_matched_records = []
        if buffer_size > 0:
            for gstin in unmatched_company['GSTIN of supplier'].unique():
                company_subset = unmatched_company[unmatched_company['GSTIN of supplier'] == gstin]
                portal_subset = portal_df[portal_df['GSTIN of supplier'] == gstin]
                
                if not portal_subset.empty:
                    for _, company_row in company_subset.iterrows():
                        close_matches = portal_subset[
                            (portal_subset['Invoice Date_x'] == company_row['Invoice Date']) &
                            (abs(portal_subset['Total'] - company_row['Total']) <= buffer_size)
                        ]
                        
                        if not close_matches.empty:
                            portal_row = close_matches.iloc[0]
                            close_matched_records.append({
                                'GSTIN': gstin,
                                'Party Name': company_row['Party Name'],
                                'Accounting Document No': company_row['Accounting Document No'],
                                'Invoice No': company_row['Invoice No'],
                                'Invoice Date': company_row['Date_Str'],
                                'Firm Total': company_row['Total'],
                                'Portal Total': portal_row['Total'],
                                'Difference': portal_row['Total'] - company_row['Total'],
                                'Match Status': 'Close',
                                'Portal Match': portal_row['Invoice number']
                            })
                            matched_invoices.add(company_row['Invoice No'])
        
        final_unmatched = company_df[~company_df['Invoice No'].isin(matched_invoices)]
        unmatched_records = []
        for _, row in final_unmatched.iterrows():
            unmatched_records.append({
                'GSTIN': row['GSTIN of supplier'],
                'Party Name': row['Party Name'],
                'Invoice No': row['Invoice No'],
                'Invoice Date': row['Date_Str'],
                'Firm Total': row['Total']
            })
        
        return matched_records + close_matched_records, unmatched_records
    
    def save_results(self, matched_records: List[Dict], unmatched_records: List[Dict], output_path: str):
        matched_df = pd.DataFrame(matched_records)
        unmatched_df = pd.DataFrame(unmatched_records)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            matched_df.to_excel(writer, sheet_name='Matched', index=False)
            unmatched_df.to_excel(writer, sheet_name='Unmatched', index=False)
        
        return len(matched_records), len(unmatched_records)