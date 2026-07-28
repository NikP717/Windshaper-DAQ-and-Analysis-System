class DataColumns:
    PROBE_COLUMNS = [ # changing these means you have to change what WindController outputs and what Old/New WindProbeManager reads
        "time_s",
        "windspeed_x",
        "windspeed_y",
        "windspeed_z",
        "static_pressure",
        "temperature_celsius",
        "atmospheric_pressure_hPa",
        "avg_pwm",
        "avg_rpm",
        "avg_target_pwm",
        "pwm_std",
        "rpm_std",
        "pwm_array",
        "rpm_array",
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
        "integral_time_scale_s",
        "integral_length_scale_m",
    ]

