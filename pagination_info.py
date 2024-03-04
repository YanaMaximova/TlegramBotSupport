from collection_editer import download_information
from kb import create_pagination_keyboard
import pandas as pd


class DataFramePaginator:
    def __init__(self, df, name_calendar, page_number = 0):
        self.df = df.reset_index(drop=True)
        self.page_number = page_number
        self.name = name_calendar

    def get_current_page(self):
        start_index = self.page_number
        end_index = (self.page_number + 1)
        return self.df.iloc[start_index:end_index]
    
    def get_page_number(self):
        return self.page_number
    
    def get_keyboard(self, info = None):
        editor_buttons = True
        keyboard = None
        if self.name == "Outstanding" or self.name == "Overdue":
            if (self.page_number + 1) >= len(self.df) and self.page_number <= 0:
                keyboard = create_pagination_keyboard(['respond'], editor_buttons=editor_buttons, info=info)
            elif (self.page_number + 1) >= len(self.df):
                keyboard = create_pagination_keyboard(['backward','respond', '|'], editor_buttons=editor_buttons, info=info)
            elif self.page_number <= 0:
                keyboard = create_pagination_keyboard(['|', 'respond', 'forward'], editor_buttons=editor_buttons, info=info)
            else:
                keyboard = create_pagination_keyboard(['backward', 'respond', 'forward'], editor_buttons=editor_buttons, info=info)
        elif self.name == "Upcoming" or self.name == "Pending":
            if (self.page_number + 1) >= len(self.df) and self.page_number <= 0:
                keyboard = create_pagination_keyboard([], editor_buttons=editor_buttons, info=info)
            elif (self.page_number + 1) >= len(self.df):
                keyboard = create_pagination_keyboard(['backward', '|'], editor_buttons=editor_buttons, info=info)
            elif self.page_number <= 0:
                keyboard = create_pagination_keyboard(['|', 'forward'], editor_buttons=editor_buttons, info=info)
            else:
                keyboard = create_pagination_keyboard(['backward', 'forward'], editor_buttons=editor_buttons, info=info)
        return keyboard
    
    def set_DataFrame(self, df):
        self.df = df.reset_index(drop=True)
    
    def increment_page(self):
        self.page_number += 1

    def decrement_page(self):
        self.page_number -= 1

    def get_DataFrame(self):
        return self.df
    
    def get_document_id(self):
        return str(self.df.loc[self.page_number, 'document_id'])
    
    def get_info(self, key):
        columns_name = self.df.columns.to_list()
        if key in columns_name:
            return self.df.loc[:, key].to_list()
        else:
            raise print('No such field')
        
    def del_info(self, key):
        self.df = delite_information(self.df, key)
        self.df = self.df.reset_index(drop=True)

    def __getitem__(self, key):
        idx = self.df['farmer_tg_id'].to_list()
        if key in idx:
            return self.df[self.df['farmer_tg_id'] == key]
        else:
            return pd.DataFrame()
