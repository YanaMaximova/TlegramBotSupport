import pandas as pd
from pagination_info import DataFramePaginator
from collection_editer import download_information


def event_brief_information(pagination_df):
    i = pagination_df.get_page_number()
    title = str(pagination_df.get_DataFrame().loc[i:i, 'title'].values[0])
    date_begin = pd.to_datetime(pagination_df.get_DataFrame().loc[i:i, 'timestamp_begin'].values[0]).strftime("%d %B %Y")
    date_end = pd.to_datetime(pagination_df.get_DataFrame().loc[i:i, 'timestamp_end'].values[0]).strftime("%d %B %Y")
    msg = f"<p><b>Title:</b> {title}<br/><b>Available From:</b> {date_begin}<br/><b>Complete By:</b> {date_end}</p>"
    status = str(pagination_df.get_DataFrame().loc[i:i, 'status'].values[0])
    if status == "refused":
        msg += f'        <hr/><p>Thank you for confirming the completion of this task!<br/><br/>Unfortunately, upon careful review, we have to ask you to resubmit your evidence. Press “More Information” for guidance.</p>'
    return msg

def event_full_information(pagination_df):
    i = pagination_df.get_page_number()
    title = str(pagination_df.get_DataFrame().loc[i:i, 'title'].values[0])
    date_begin = pd.to_datetime(pagination_df.get_DataFrame().loc[i:i, 'timestamp_begin'].values[0]).strftime("%d %B %Y")
    date_end = pd.to_datetime(pagination_df.get_DataFrame().loc[i:i, 'timestamp_end'].values[0]).strftime("%d %B %Y")
    info = str(pagination_df.get_DataFrame().loc[i:i, 'info'].values[0])
    type = str(pagination_df.get_DataFrame().loc[i:i, 'type'].values[0]).replace('_', ' ')
    msg = f"*Title:* {title}\n*Task Description:* {info}\n*Reporting style:* {type}\n*Available From:* {date_begin}\n*Complete By:* {date_end}"
    return msg

def event_without_confirm(pagination_df):
    i = pagination_df.get_page_number()
    title = str(pagination_df.get_DataFrame().loc[i:i, 'title'].values[0])
    date_begin = pd.to_datetime(pagination_df.get_DataFrame().loc[i:i, 'timestamp_begin'].values[0]).strftime("%d %B %Y")
    date_end = pd.to_datetime(pagination_df.get_DataFrame().loc[i:i, 'timestamp_end'].values[0]).strftime("%d %B %Y")
    msg = f"Have you completed *{title}* between *{date_begin}* and *{date_end}*?"
    return msg
