import pandas as pd
import ipywidgets as widgets
from IPython.display import display, clear_output
import random
import re

data = {
    'Riven 1 [20]': [1, 1, 1, 2, 2, 3, 5, 6, 9, 10, 13, 14],
    'Riven 2 [15]': [1.0, 1.0, 2.0, 2.0, 3.0, 4.0, 5.0, 5.0, 7.0, 12.0, 19.0, None],
    'Riven 3 [15]': [2, 2, 3, 3, 4, 5, 6, 6, 8, 8, 10, 12],
    'Riven 4 [15]': [1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0, 5.0, None, None, None],
    'Riven 5 [15]': [1.0, 1.0, 1.0, 1.0, 2.0, 4.0, 5.0, 5.0, 6.0, 7.0, 8.0, None],
    'VICP [20]': [1, 1, 2, 2, 3, 3, 4, 4, 6, 9, 14, 21]
}


# Global variable to track the position of the last new patient
last_new_patient_pos = None

# Function to extract the census cap from the column name
def extract_census_cap(column_name):
    match = re.search(r'\[(\d+)\]', column_name)
    if match:
        return int(match.group(1))
    else:
        return None

# Function to calculate LOSAC scores
def calculate_losac(dataframe):
    losac_scores = {}

    # Calculate the minimum census cap among all teams
    min_census_cap = min([extract_census_cap(team) for team in dataframe.columns])

    for team in dataframe.columns:
        census_cap = extract_census_cap(team)
        if census_cap is not None:
            team_census = dataframe[team].dropna()
            if team_census.count() < census_cap:
                median_los = team_census.median() if team_census.count() > 0 else 1
                losac_scores[team] = (team_census.count() - (census_cap - min_census_cap)) / median_los
            else:
                losac_scores[team] = float('inf')
    return losac_scores

# Function to handle discharging patients
def discharge_patient(selected_cell):
    global df

    # Discharge the selected patient
    team, patient = selected_cell.split(',')
    df.at[int(patient), team] = pd.NA

    # Sort each team's list in ascending order of LOS
    df = df.apply(lambda x: pd.to_numeric(x, errors='coerce').sort_values().reset_index(drop=True))

    # Redraw the table
    clear_output(wait=True)
    draw_table(calculate_losac(df))

# Function to admit a new patient
def admit_new_patient(_):
    global df, last_new_patient_pos

    # Calculate LOSAC scores with current census
    losac_scores = calculate_losac(df)

    # Filter out teams at full capacity
    eligible_teams = {team: losac for team, losac in losac_scores.items() if df[team].count() < extract_census_cap(team)}

    if eligible_teams:
        # Find the minimum LOSAC score
        min_losac = min(eligible_teams.values())
        # Get all teams that have the minimum LOSAC score
        tied_teams = [team for team, losac in eligible_teams.items() if losac == min_losac]

        # Check if there's a tie in both LOSAC and census
        if len(tied_teams) > 1:
            # Calculate the number of open slots remaining for each tied team
            open_slots_remaining = {team: extract_census_cap(team) - df[team].count() for team in tied_teams}

            # Find the team with the maximum open slots remaining
            max_open_slots = max(open_slots_remaining.values())
            teams_with_max_open_slots = [team for team in tied_teams if open_slots_remaining[team] == max_open_slots]

            # If there's still a tie, break it based on the higher census cap
            if len(teams_with_max_open_slots) > 1:
                max_census_cap = max([extract_census_cap(team) for team in teams_with_max_open_slots])
                teams_with_max_census_cap = [team for team in teams_with_max_open_slots if extract_census_cap(team) == max_census_cap]
                selected_team = random.choice(teams_with_max_census_cap)
            else:
                selected_team = teams_with_max_open_slots[0]
        else:
            selected_team = tied_teams[0]

        # Insert new patient in the first position (index 0) for the selected team
        # Shift existing patients down
        df[selected_team] = df[selected_team].shift(1)
        # Set the first position to 1 for the new patient
        df.at[0, selected_team] = 1
        # Update the position of the last new patient to color the cell
        last_new_patient_pos = (0, selected_team)
        # Re-sort only the affected team's column
        df[selected_team] = pd.to_numeric(df[selected_team], errors='coerce').sort_values().reset_index(drop=True)
    else:
        print("All teams have reached their census cap or there is an error.")

    # Redraw the table with the updated LOSAC
    clear_output(wait=True)
    draw_table(calculate_losac(df))


# Function to increment the LOS for all patients (start new day)
def increment_day(_):
    global df

    # Increment LOS by 1 for all patients
    df = df.applymap(lambda x: x + 1 if pd.notna(x) else x)

    # Sort each team's list in ascending order of LOS
    df = df.apply(lambda x: pd.to_numeric(x, errors='coerce').sort_values().reset_index(drop=True))

    # Redraw the table with updated LOSAC
    clear_output(wait=True)
    draw_table(calculate_losac(df))

# Make sure to update the create_styled_button function with the new parameters
def create_styled_button(description, pos, is_new_patient, is_green, is_blue):
    button = widgets.Button(description=description, layout=widgets.Layout(width='auto'))
    if is_new_patient:
        button.style.button_color = 'lightcoral'  # Light red color for new patient
    elif is_green:
        button.style.button_color = 'lightgreen'  # Light green for patients with LOS of 1
    elif is_blue:
        button.style.button_color = 'lightblue'   # Light blue for patients below census cap
    return button

def draw_table(losac_scores):
    global df, last_new_patient_pos

    # Create the table grid with the number of rows in the DataFrame
    num_rows = df.shape[0]
    # Adjusting the number of rows to account for the two-line header
    table = widgets.GridspecLayout(num_rows + 2, df.shape[1] + 1)

    # Add a two-line header for each column
    for j, team in enumerate(df.columns):
        # First line: Team Name and Census Cap
        table[0, j + 1] = widgets.HTML(value=f"<center>{team}</center>")
        # Second line: LOSAC Score
        losac_score = losac_scores[team]
        table[1, j + 1] = widgets.HTML(value=f"<center>{losac_score:.2f}</center>")

    # Adjust the row index in the loop for the table cells
    for i in range(num_rows):
        table[i + 2, 0] = widgets.Label(value=str(i + 1))

    for i in range(num_rows):
        for j in range(df.shape[1]):
            cell_value = df.iloc[i, j] if i < df.shape[0] else ''
            is_new_patient = ((i, df.columns[j]) == last_new_patient_pos and cell_value == 1)
            is_green = cell_value == 1 and not is_new_patient
            team_census_cap = extract_census_cap(df.columns[j])
            is_blue = i < team_census_cap  # Check if the cell is within the census cap for that team
            button = create_styled_button(str(cell_value) if pd.notna(cell_value) else ' ',
                                          pos=(i, j),
                                          is_new_patient=is_new_patient,
                                          is_green=is_green,
                                          is_blue=is_blue)
            table[i + 2, j + 1] = button  # Adjusted row index

            button.on_click(lambda btn, x=i, y=j: discharge_patient(f"{df.columns[y]},{x}"))

    display(table)

    # Add "New Patient" and "Next Day" buttons
    new_patient_button = widgets.Button(description="New Patient")
    new_patient_button.on_click(admit_new_patient)
    display(new_patient_button)

    next_day_button = widgets.Button(description="Next Day")
    next_day_button.on_click(increment_day)
    display(next_day_button)

    # Add "Reset Table" button
    reset_table_button = widgets.Button(description="Reset Table")
    reset_table_button.on_click(reset_table)
    display(reset_table_button)

def reset_table(_):
    global df, initial_losac_scores, last_new_patient_pos

    # Reset the last new patient position
    last_new_patient_pos = None

    # Reload the DataFrame from the Excel spreadsheet
    df = pd.DataFrame(data)

    # Initialize DataFrame to have the maximum census cap as the number of rows
    max_census_cap = max([extract_census_cap(team) for team in df.columns])
    df = df.reindex(range(max_census_cap))

    # Sort each team's list in ascending order of LOS
    df = df.apply(lambda x: pd.to_numeric(x, errors='coerce').sort_values().reset_index(drop=True))

    # Recalculate the LOSAC scores
    initial_losac_scores = calculate_losac(df)

    # Redraw the table
    clear_output(wait=True)
    draw_table(initial_losac_scores)

# Read the initial census
df = pd.DataFrame(data)

# Initialize dataframe to have the maximum census cap as the number of rows
max_census_cap = max([extract_census_cap(team) for team in df.columns])
df = df.reindex(range(max_census_cap))

# Sort each team's list in ascending order of LOS
df = df.apply(lambda x: pd.to_numeric(x, errors='coerce').sort_values().reset_index(drop=True))

# Calculate initial LOSAC scores
initial_losac_scores = calculate_losac(df)

# Draw the initial table
draw_table(initial_losac_scores)