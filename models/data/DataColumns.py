class DataColumns:
    PROBE_COLUMNS = [ # changing these means you have to change what WindController outputs and what Old/New WindProbeManager reads
        "time_s",
        "windspeed_x",
        "windspeed_y",
        "windspeed_z",
        "static_pressure",
        "temperature_celsius",
        "atmospheric_pressure_hPa",
        "avg_up_pwm",
        "avg_up_rpm",
        "std_up_rpm",
        "avg_down_pwm",
        "avg_down_rpm",
        "std_down_rpm",
        "rpm_up_array",
        "rpm_down_array"
    ]

    META_COLUMNS = [ # u wouldnt benefit from changing this because the manual metadata exists already
        "probe_id",
        "fan_pwm",
        "upstream_pwm",
        "downstream_pwm",
        "distance_from_wall",
        "probe_pos_x",
        "probe_pos_y",
        "repeat",
        "wind_fq",
        "wind_amplitude",
        "wind_avg",
    ]

    SUMMARY_COLUMNS = [ # changing this means you have to change what WindData calculates as summary data
        "mean_speed_mps",
        "std_fluctuation_mps",
        "TI_percent",
        "rolling_mean_variation",
        "rolling_std_variation",
        "ADF_pvalue",
    ]

