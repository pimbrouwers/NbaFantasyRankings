import csv
import json
import numpy
import os
import pandas
import sys
import urllib.request

class NbaStatsParser:

	per_game_file = "pergame.csv"
	per_36_file = "per36.csv"

	def __init__(self, year, dateFrom, dateTo, cols):
		# setup season to parse
		self.season_id = "{}-{}".format(year, str(year + 1)[-2:])

		# date constraint (if any)
		self.dateFrom = dateFrom if not (dateFrom is None) else ""
		self.dateTo = dateTo if not (dateTo is None) else ""

		# columns to perform analysis on
		if not (cols is None):
			self.cols = cols
		else:
			self.cols = ["FG_PCT","FG3M","FT_PCT","REB","AST","TOV","STL","BLK","PTS"]

	def write_csv(self, file, stats):
		with open(file, 'w', newline='') as f:
			writer = csv.writer(f)
			writer.writerow(stats["headers"])
			writer.writerows(stats["stats"])

	def download_stats(self, per_mode):
		url = "https://stats.nba.com/stats/leaguedashplayerstats?College=&Conference=&Country=&DateFrom={}&DateTo={}&Division=&DraftPick=&DraftYear=&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode={}&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season={}&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=&Weight=".format(self.dateFrom, self.dateTo, per_mode, self.season_id)	
		user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
		headers = {'User-Agent': user_agent}
		
		req = urllib.request.Request(url, None, headers)		
		stats = []

		with urllib.request.urlopen(req) as resp:
			data = json.loads(resp.read().decode())
			
			return { "headers": data["resultSets"][0]["headers"], "stats": data["resultSets"][0]["rowSet"] }

	def analyze_stats(self):
		per_game = self.download_stats("PerGame")		
		per_36 = self.download_stats("Per36")

		per_game_df = pandas.DataFrame(data = per_game["stats"], columns = per_game["headers"])
		per_36_df = pandas.DataFrame(data = per_36["stats"], columns = per_36["headers"])
		
		for col in self.cols:
			col_zscore = col + "_ZSCORE"		
			if(col == "TOV"):
				per_game_df[col_zscore] = ((per_game_df[col] - per_game_df[col].mean())/per_game_df[col].std(ddof=0)) * -1
				per_36_df[col_zscore] = ((per_36_df[col] - per_36_df[col].mean())/per_36_df[col].std(ddof=0)) * -1
			else:
				per_game_df[col_zscore] = (per_game_df[col] - per_game_df[col].mean())/per_game_df[col].std(ddof=0)
				per_36_df[col_zscore] = (per_36_df[col] - per_36_df[col].mean())/per_36_df[col].std(ddof=0)

		per_game_df["ZSCORE"] = per_game_df[self.cols].sum(axis="columns")
		per_36_df["ZSCORE"] = per_36_df[self.cols].sum(axis="columns")
		
		output_df = per_game_df[["PLAYER_ID", "PLAYER_NAME", "AGE", "GP", "MIN", "ZSCORE"]].join(per_36_df[["PLAYER_ID", "ZSCORE"]], lsuffix = "_PERGAME", rsuffix = "_PER36")
		output_df.drop(["PLAYER_ID_PERGAME", "PLAYER_ID_PER36"], inplace = True, axis = 1)
		output_df["ZSCORE_DIFF"] = output_df["ZSCORE_PER36"] - output_df["ZSCORE_PERGAME"]
		
		self.save_analysis(output_df)
		
	def save_analysis(self, df):
		filename = "overall_{}_{}".format(self.season_id, "-".join(self.cols))

		if self.dateFrom:
			filename += "_" + self.dateFrom

		if self.dateTo:
			filename += "_" + self.dateTo

		filename += ".csv"

		df.sort_values(["ZSCORE_PERGAME", "ZSCORE_PER36"], ascending = [False, False]).to_csv(filename, mode = 'w', index=False)

def main():
	year = None
	dateFrom = None
	dateTo = None
	cols = None

	# parse year
	try:	
		year = int(sys.argv[1])
	except ValueError:
		print("Invalid year")
		sys.exit(0)

	# parse dateFrom & dateTo
	if (len(sys.argv) >= 4):
		dateFrom = sys.argv[2]
		dateTo = sys.argv[3]

	# parse cols	
	if (len(sys.argv) >= 5):
		colStr = sys.argv[4]
		cols = colStr.split(",")
	
	parser = NbaStatsParser(year, dateFrom, dateTo, cols)
	parser.analyze_stats()

if __name__ == "__main__":
    main()
