"""
This module downloads the U.S. total nonfarm payrolls seasonally adjusted
(PAYEMS) monthly time series from the St. Louis Federal Reserve's FRED system
(https://fred.stlouisfed.org/series/PAYEMS) or loads it from this directory and
organizes it into series of consecutive positive monthly gain streaks.

This module defines the following function(s):
    get_usempl_data()
    usempl_npp()
"""

# Import packages
import numpy as np
import pandas as pd
import pandas_datareader as pddr
import datetime as dt
import os
from bokeh.io import output_file
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, Title, Legend, HoverTool

# from bokeh.models import Label
from bokeh.palettes import Category20, Plasma256, Viridis8

"""
Define functions
"""


def get_usempl_data(
    end_date_str="2024-02-02",
    download_from_internet=True,
    include_annual_1919=True,
):
    """
    This function either downloads or reads in the U.S. total nonfarm payrolls
    seasonally adjusted monthly data series (PAYEMS).

    Args:
        frwd_mths_max (int): maximum number of months forward from the peak
            month to plot
        bckwd_mths_max (int): maximum number of months backward from the peak
            month to plot
        end_date_str (str): end date of PAYEMS time series in 'YYYY-mm-dd'
            format
        download_from_internet (bool): =True if download data from
            fred.stlouisfed.org, otherwise read data in from local directory

    Other functions and files called by this function:
        usempl_[yyyy-mm-dd].csv

    Files created by this function:
        usempl_[yyyy-mm-dd].csv
        usempl_pk_[yyyy-mm-dd].csv

    Returns:
        usempl_pk (DataFrame): N x 46 DataFrame of mths_frm_peak, Date{i},
            Close{i}, and close_dv_pk{i} for each of the 15 recessions for the
            periods specified by bkwd_days_max and frwd_days_max
        end_date_str2 (str): actual end date of DJIA time series in
            'YYYY-mm-dd' format. Can differ from the end_date input to this
            function if the final data for that day have not come out yet
            (usually 2 hours after markets close, 6:30pm EST), or if the
            end_date is one on which markets are closed (e.g. weekends and
            holidays). In this latter case, the pandas_datareader library
            chooses the most recent date for which we have DJIA data.
        peak_vals (list): list of peak DJIA value at the beginning of each of
            the last 15 recessions
        peak_dates (list): list of string date (YYYY-mm-dd) of peak DJIA value
            at the beginning of each of the last 15 recessions
        rec_label_yr_lst (list): list of string start year and end year of each
            of the last 15 recessions
        rec_label_yrmth_lst (list): list of string start year and month and end
            year and month of each of the last 15 recessions
        rec_beg_yrmth_lst (list): list of string start year and month of each
            of the last 15 recessions
        maxdate_rng_lst (list): list of tuples with start string date and end
            string date within which range we define the peak DJIA value at the
            beginning of each of the last 15 recessions
    """
    end_date = dt.datetime.strptime(end_date_str, "%Y-%m-%d")

    # Name the current directory and make sure it has a data folder
    cur_path = os.path.split(os.path.abspath(__file__))[0]
    data_fldr = "data"
    data_dir = os.path.join(cur_path, data_fldr)
    if not os.access(data_dir, os.F_OK):
        os.makedirs(data_dir)

    filename = "usempl_" + end_date_str + ".csv"

    if download_from_internet:
        # Download the employment data directly from fred.stlouisfed.org
        # (requires internet connection)
        start_date = dt.datetime(1939, 1, 1)
        usempl_df = pddr.fred.FredReader(
            symbols="PAYEMS", start=start_date, end=end_date
        ).read()
        usempl_df = pd.DataFrame(usempl_df).sort_index()  # Sort old to new
        usempl_df = usempl_df.reset_index(level=["DATE"])
        usempl_df = usempl_df.rename(columns={"DATE": "Date"})
        end_date_str2 = usempl_df["Date"].iloc[-1].strftime("%Y-%m-%d")
        end_date = dt.datetime.strptime(end_date_str2, "%Y-%m-%d")
        filename = "usempl_" + end_date_str2 + "_streaks.csv"
        usempl_df.to_csv(os.path.join(data_dir, filename), index=False)
        if include_annual_1919:
            # Merge in U.S. annual average nonfarm payroll employment (not
            # seasonally adjusted) 1919-1938. Date values for annual data are set
            # to July 1 of that year. These data are taken from Table 1 on page 1
            # of "Employment, Hours, and Earnings, United States, 1909-90, Volume
            # I," Bulletin of the United States Bureau of Labor Statistics, No.
            # 2370, March 1991.
            # <https://fraser.stlouisfed.org/title/employment-earnings-united-
            # states-189/employment-hours-earnings-united-states-1909-90-5435/
            # content/pdf/emp_bmark_1909_1990_v1>
            filename_annual = "usempl_anual_1919-1938.csv"
            ann_data_file_path = os.path.join(data_dir, filename_annual)
            usempl_ann_df = pd.read_csv(
                ann_data_file_path,
                names=["Date", "PAYEMS"],
                parse_dates=["Date"],
                skiprows=1,
                na_values=[".", "na", "NaN"],
            )
            usempl_df = pd.concat(
                [usempl_ann_df, usempl_df], ignore_index=True
            )
            usempl_df = usempl_df.sort_values(by="Date")
            usempl_df = usempl_df.reset_index(drop=True)
            usempl_df.to_csv(os.path.join(data_dir, filename), index=False)
            # Add other months to annual data 1919-01-01 to 1938-12-01 and fill in
            # artificial employment data by cubic spline interpolation
            months_df = pd.DataFrame(
                pd.date_range("1919-01-01", "1938-12-01", freq="MS"),
                columns=["Date"],
            )
            usempl_df = pd.merge(
                usempl_df,
                months_df,
                left_on="Date",
                right_on="Date",
                how="outer",
            )
            usempl_df = usempl_df.sort_values(by="Date")
            usempl_df = usempl_df.reset_index(drop=True)

            # Insert cubic spline interpolation for missing PAYEMS values
            usempl_df.loc[:242, "PAYEMS"] = usempl_df.loc[
                :242, "PAYEMS"
            ].interpolate(method="cubic")
    else:
        # Import the data as pandas DataFrame
        end_date_str2 = end_date_str
        data_file_path = os.path.join(data_dir, filename)
        usempl_df = pd.read_csv(
            data_file_path,
            names=["Date", "PAYEMS"],
            parse_dates=["Date"],
            skiprows=1,
            na_values=[".", "na", "NaN"],
        )

    usempl_df = usempl_df.dropna()
    usempl_df = usempl_df.reset_index(drop=True)
    print(
        "End date of U.S. employment series is", end_date.strftime("%Y-%m-%d")
    )
    usempl_df["empl_mth_gain"] = usempl_df["PAYEMS"].diff()

    return usempl_df, end_date_str2


def usempl_streaks(
    usempl_end_date="today",
    download_from_internet=True,
    include_annual_1919=True,
    html_show=True,
):
    """
    This function creates the HTML and JavaScript code for the dynamic
    visualization of the US positive employment streaks from 1919 to the given
    end date.

    Args:
        usempl_end_date (str): either 'today' or the end date of PAYEMS time
            series in 'YYYY-mm-dd' format
        download_from_internet (bool): =True if download data from St. Louis
            Federal Reserve's FRED system
            (https://fred.stlouisfed.org/series/PAYEMS), otherwise read data in
            from local directory
        html_show (bool): =True if open dynamic visualization in browser once
            created

    Other functions and files called by this function:
        get_usempl_data()

    Files created by this function:
       images/usempl_[yyyy-mm-dd].html

    Returns: fig, end_date_str
    """
    # Create directory if images directory does not already exist
    cur_path = os.path.split(os.path.abspath(__file__))[0]
    image_fldr = "images"
    image_dir = os.path.join(cur_path, image_fldr)
    if not os.access(image_dir, os.F_OK):
        os.makedirs(image_dir)

    if usempl_end_date == "today":
        end_date = dt.date.today()  # Go through today
    else:
        end_date = dt.datetime.strptime(usempl_end_date, "%Y-%m-%d")

    end_date_str = end_date.strftime("%Y-%m-%d")

    usempl_df, end_date_str2 = get_usempl_data(
        end_date_str=end_date_str,
        download_from_internet=download_from_internet,
        include_annual_1919=include_annual_1919,
    )

    print("PAYEMS data downloaded on " + end_date_str + ":")
    print(
        "    has start PAYEMS data month of "
        + usempl_df.loc[0, "Date"].strftime("%Y-%m")
        + ","
    )
    print("    and end PAYEMS data month of " + end_date_str2 + ".")

    end_date2 = dt.datetime.strptime(end_date_str2, "%Y-%m-%d")

    strk_df_lst = []
    strk_cds_lst = []
    strk_label_lst = []
    min_gain_val_lst = []
    max_gain_val_lst = []
    min_cum_val_lst = []
    max_cum_val_lst = []
    min_mth_val_lst = []
    max_mth_val_lst = []
    strk_num = 0
    strk_mths = 0
    strk_cum = 0
    for i in range(usempl_df.shape[0]):
        if usempl_df.loc[i, "empl_mth_gain"] > 0:
            if strk_mths == 0:
                j = i
                strk_num += 1
                strk_df = pd.DataFrame(
                    columns=[
                        "Date",
                        "PAYEMS",
                        "empl_mth_gain",
                        "strk_mths",
                        "strk_cum",
                        "strk_mths_tot",
                        "strk_avg_emp_gain",
                        "strk_cum_tot",
                    ]
                )
                strk_start_mth_str = usempl_df.loc[i, "Date"].strftime("%Y-%m")
            strk_df.loc[i - j, ["Date", "PAYEMS", "empl_mth_gain"]] = (
                usempl_df.loc[i, ["Date", "PAYEMS", "empl_mth_gain"]]
            )
            strk_mths += 1
            strk_df.loc[i - j, "strk_mths"] = strk_mths
            strk_cum += usempl_df.loc[i, "empl_mth_gain"]
            strk_df.loc[i - j, "strk_cum"] = strk_cum
            if i == usempl_df.shape[0] - 1:
                strk_end_mth_str = usempl_df.loc[i, "Date"].strftime("%Y-%m")
                strk_label = strk_start_mth_str + " to " + strk_end_mth_str
                strk_label_lst.append(strk_label)
                strk_df["strk_mths_tot"] = strk_mths
                strk_df["strk_avg_emp_gain"] = strk_cum / strk_mths
                strk_df["strk_cum_tot"] = strk_cum
                strk_df_lst.append(strk_df)
                strk_cds_lst.append(ColumnDataSource(strk_df))
                min_gain_val_lst.append(strk_df["empl_mth_gain"].min())
                max_gain_val_lst.append(strk_df["empl_mth_gain"].max())
                min_cum_val_lst.append(strk_df["strk_cum"].min())
                max_cum_val_lst.append(strk_df["strk_cum"].max())
                min_mth_val_lst.append(strk_df["strk_mths"].min())
                max_mth_val_lst.append(strk_df["strk_mths"].max())
        elif (
            usempl_df.loc[i, "empl_mth_gain"] <= 0
            and usempl_df.loc[i - 1, "empl_mth_gain"] > 0
            and i > 0
        ):
            strk_df["strk_mths_tot"] = strk_mths
            strk_df["strk_avg_emp_gain"] = strk_cum / strk_mths
            strk_df["strk_cum_tot"] = strk_cum
            strk_mths = 0
            strk_cum = 0
            strk_end_mth_str = usempl_df.loc[i - 1, "Date"].strftime("%Y-%m")
            strk_label = strk_start_mth_str + " to " + strk_end_mth_str
            strk_label_lst.append(strk_label)
            strk_df_lst.append(strk_df)
            strk_cds_lst.append(ColumnDataSource(strk_df))
            min_gain_val_lst.append(strk_df["empl_mth_gain"].min())
            max_gain_val_lst.append(strk_df["empl_mth_gain"].max())
            min_cum_val_lst.append(strk_df["strk_cum"].min())
            max_cum_val_lst.append(strk_df["strk_cum"].max())
            min_mth_val_lst.append(strk_df["strk_mths"].min())
            max_mth_val_lst.append(strk_df["strk_mths"].max())

    print("Number of streaks:", strk_num)

    # Create Bokeh plot of PAYEMS normalized peak plot figure
    fig_title = (
        "Consecutive US monthly employment gain streaks since "
        + usempl_df.loc[0, "Date"].strftime("%Y")
    )
    filename = "usempl_streaks_" + end_date_str2 + ".html"
    output_file(os.path.join(image_dir, filename), title=fig_title)

    # Format the tooltip
    tooltips = [
        ("Date", "@Date{%F}"),
        ("Current month in streak", "@strk_mths{0.}"),
        ("Total months in streak", "@strk_mths_tot{0.}"),
        ("Monthly employment gain", "@empl_mth_gain{0.}"),
        ("Cumulative employment gain", "@strk_cum{0.}"),
        ("Total cumulative employment gain", "@strk_cum_tot{0.}"),
        ("Avg. monthly employment gain", "@strk_avg_emp_gain{0.}"),
    ]

    # Solve for minimum and maximum PAYEMS/Peak values in monthly main display
    # window in order to set the appropriate xrange and yrange
    min_cum_val = min(min_cum_val_lst)
    max_cum_val = max(max_cum_val_lst)
    min_mth_val = min(min_mth_val_lst)
    max_mth_val = max(max_mth_val_lst)

    datarange_cum_vals = max_cum_val - min_cum_val
    datarange_mth_vals = int(min_mth_val + max_mth_val)
    fig_buffer_pct = 0.05
    fig = figure(
        plot_height=500,
        plot_width=800,
        x_axis_label="Months in streak",
        y_axis_label="Cumulative employment gains in streak",
        y_range=(
            min_cum_val - fig_buffer_pct * datarange_cum_vals,
            max_cum_val + fig_buffer_pct * datarange_cum_vals,
        ),
        x_range=(
            (min_mth_val - fig_buffer_pct * datarange_mth_vals),
            (max_mth_val + fig_buffer_pct * datarange_mth_vals),
        ),
        tools=[
            "save",
            "zoom_in",
            "zoom_out",
            "box_zoom",
            "pan",
            "undo",
            "redo",
            "reset",
            "hover",
            "help",
        ],
        toolbar_location="left",
    )
    fig.title.text_font_size = "18pt"
    fig.toolbar.logo = None
    fig_lst = []
    label_items_lst = []
    j = -1
    for i in range(strk_num):
        if max_cum_val_lst[i] > 10_000 or max_mth_val_lst[i] > 40:
            j += 1
            li = fig.line(
                x="strk_mths",
                y="strk_cum",
                source=strk_cds_lst[i],
                color=Viridis8[7 - j],
                # color=Plasma256[255 - int(i * (256 - 1) / (strk_num - 1))],
                line_width=4,
                alpha=0.7,
                muted_alpha=0.15,
            )
            label_items_lst.append((strk_label_lst[i], [li]))
        else:
            li = fig.line(
                x="strk_mths",
                y="strk_cum",
                source=strk_cds_lst[i],
                color="orange",
                line_width=2,
                alpha=0.7,
                muted_alpha=0.15,
            )
        fig_lst.append(li)

    # # Create the tick marks for the x-axis and set x-axis labels
    # major_tick_labels = []
    # major_tick_list = []
    # for i in range(-bkwd_mths_max, frwd_mths_max + 1):
    #     if i % 2 == 0:  # indicates even integer
    #         major_tick_list.append(int(i))
    #         if i < 0:
    #             major_tick_labels.append(str(i) + 'mth')
    #         elif i == 0:
    #             major_tick_labels.append('peak')
    #         elif i > 0:
    #             major_tick_labels.append('+' + str(i) + 'mth')

    # # minor_tick_list = [item for item in range(-bkwd_mths_max,
    # #                                           frwd_mths_max + 1)]
    # major_tick_dict = dict(zip(major_tick_list, major_tick_labels))
    # fig.xaxis.ticker = major_tick_list
    # fig.xaxis.major_label_overrides = major_tick_dict

    # # Add legend with set labels
    # legend = Legend(location="center")
    # fig.add_layout(legend, "right")

    # Add legend
    legend = Legend(items=label_items_lst, location="center")
    fig.add_layout(legend, "right")

    # # Add legend
    # legend = Legend(
    #     items=[
    #         (rec_label_yrmth_lst[0], [l0]),
    #         (rec_label_yrmth_lst[1], [l1]),
    #         (rec_label_yrmth_lst[2], [l2]),
    #         (rec_label_yrmth_lst[3], [l3]),
    #         (rec_label_yrmth_lst[4], [l4]),
    #         (rec_label_yrmth_lst[5], [l5]),
    #         (rec_label_yrmth_lst[6], [l6]),
    #         (rec_label_yrmth_lst[7], [l7]),
    #         (rec_label_yrmth_lst[8], [l8]),
    #         (rec_label_yrmth_lst[9], [l9]),
    #         (rec_label_yrmth_lst[10], [l10]),
    #         (rec_label_yrmth_lst[11], [l11]),
    #         (rec_label_yrmth_lst[12], [l12]),
    #         (rec_label_yrmth_lst[13], [l13]),
    #         (rec_label_yrmth_lst[14], [l14]),
    #     ],
    #     location="center",
    # )
    # fig.add_layout(legend, "right")

    # # Add label to current recession low point
    # fig.text(x=[12, 12, 12, 12], y=[0.63, 0.60, 0.57, 0.54],
    #          text=['2020-03-23', 'DJIA: 18,591.93', '63.3% of peak',
    #                '39 days from peak'],
    #          text_font_size='8pt', angle=0)

    # label_text = ('Recent low \n 2020-03-23 \n DJIA: 18,591.93 \n '
    #               '63\% of peak \n 39 days from peak')
    # fig.add_layout(Label(x=10, y=0.65, x_units='screen', text=label_text,
    #                      render_mode='css', border_line_color='black',
    #                      border_line_alpha=1.0,
    #                      background_fill_color='white',
    #                      background_fill_alpha=1.0))

    # Add title and subtitle to the plot
    fig.add_layout(
        Title(
            text=fig_title,
            text_font_style="bold",
            text_font_size="16pt",
            align="center",
        ),
        "above",
    )
    # fig_title2 = "Progression of U.S. total nonfarm employment"
    # fig_title3 = "(PAYEMS, seasonally adjusted) in last 15 recessions"
    # fig.add_layout(
    #     Title(
    #         text=fig_title3,
    #         text_font_style="bold",
    #         text_font_size="16pt",
    #         align="center",
    #     ),
    #     "above",
    # )
    # fig.add_layout(
    #     Title(
    #         text=fig_title2,
    #         text_font_style="bold",
    #         text_font_size="16pt",
    #         align="center",
    #     ),
    #     "above",
    # )

    # Add source text below figure
    updated_date_str = (
        end_date.strftime("%B")
        + " "
        + end_date.strftime("%d").lstrip("0")
        + ", "
        + end_date.strftime("%Y")
    )
    fig.add_layout(
        Title(
            text="Source: Richard W. Evans (@RickEcon), "
            + "historical PAYEMS data from FRED and BLS, "
            + "updated "
            + updated_date_str
            + ".",
            align="left",
            text_font_size="3mm",
            text_font_style="italic",
        ),
        "below",
    )
    fig.legend.click_policy = "mute"

    # Add the HoverTool to the figure
    fig.add_tools(
        HoverTool(
            tooltips=tooltips,
            toggleable=False,
            formatters={"@Date": "datetime"},
        )
    )

    if html_show:
        show(fig)

    return fig, end_date_str


if __name__ == "__main__":
    # execute only if run as a script
    fig, end_date_str = usempl_streaks()
