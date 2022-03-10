from freqtrade.strategy import IStrategy, merge_informative_pair
from typing import Dict, List
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.exchange import timeframe_to_minutes
import datetime

class Leveraged(IStrategy):

    def version(self) -> str:
        return "v0.0.2"

    minimal_roi = { "0": 100 }

    stoploss = -0.15

    trailing_stop = True

    sell_profit_only=True

    timeframe = '1m'

## INIZIO gestione dual timing
    informative_timeframe = '5m'

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        if self.config['runmode'].value in ('backtest', 'hyperopt'):
            assert (timeframe_to_minutes(self.timeframe) <= 5), "Backtest this strategy in 5m or 1m timeframe."

        if self.timeframe == self.informative_timeframe:
            dataframe = self.do_indicators(dataframe, metadata)
        else:
            if not self.dp:
                return dataframe

            informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.informative_timeframe)

            informative = self.do_indicators(informative.copy(), metadata)

            dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True)
            skip_columns = [(s + "_" + self.informative_timeframe) for s in ['date', 'open', 'high', 'low', 'close', 'volume']]
            dataframe.rename(columns=lambda s: s.replace("_{}".format(self.informative_timeframe), "") if (not s in skip_columns) else s, inplace=True)

        return dataframe
## FINE gestione dual timing

## Trailing stoploss with positive offset
    use_custom_stoploss = True

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        if current_profit < 0.008:
            return -1 # return a value bigger than the initial stoploss to keep using the initial stoploss

        # After reaching the desired offset, allow the stoploss to trail by half the profit
        desired_stoploss = current_profit / 2

        # Use a minimum of 2.5% and a maximum of 5%
        return max(min(desired_stoploss, 0.10), 0.008)

### FINE  Trailing stoploss with positive offset

    def do_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['cci'] = ta.CCI(dataframe)

        return dataframe

#        dataframe['ema3'] = ta.EMA(dataframe, timeperiod=3)
#        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
#        dataframe['go_long'] = qtpylib.crossed_above(dataframe['ema3'], dataframe['ema5']).astype('int')
#        dataframe['go_short'] = qtpylib.crossed_below(dataframe['ema3'], dataframe['ema5']).astype('int')
#        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe['macd'], dataframe['macdsignal'])
                #& (dataframe['cci'] <= -50.0)
            ),
            'buy'] = 1

        return dataframe

#        dataframe.loc[
#            qtpylib.crossed_above(dataframe['go_long'], 0)
#        ,
#        'buy'] = 1
#
#        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                qtpylib.crossed_below(dataframe['macd'], dataframe['macdsignal'])
                #& (dataframe['cci'] >= 100.0)
            ),
            'sell'] = 1

        return dataframe

#        dataframe.loc[
#            qtpylib.crossed_above(dataframe['go_short'], 0)
#        ,
#        'sell'] = 1
#
#        return dataframe
