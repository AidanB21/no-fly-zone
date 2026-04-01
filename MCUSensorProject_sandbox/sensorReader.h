/// Created Su 2/22/26 @ 12pm  by Kailash Pillai

/// Simple reads sensor data from the MCU and stuff

#ifndef SENSORREADER_H
#define SENSORREADER_H

//
// Included Files
//
#include "driverlib.h"
#include "device.h"
#include "board.h"
#include "c2000ware_libraries.h"
#include <stdio.h>



/// Defines ///
#define I2C_TIMEOUT   100000UL   // How long to wait before timing out of the I2C functions

// Struct prototypes
typedef struct {
        /// Raw Sensor Values ///
    uint16_t raw_MQ3;
    uint16_t raw_MQ135;
    uint16_t raw_MQ138;
    uint16_t raw_MQ131;
    uint16_t raw_TGS2602;

        /// Converted Sensor Values ///
    uint16_t converted_MQ3;
    uint16_t converted_MQ135;
    uint16_t converted_MQ138;
    uint16_t converted_MQ131;
    uint16_t converted_TGS2602;

        /// Temp + Humididty + Pressure ///
    uint32_t raw_temp;
    uint32_t raw_humidity;
    
    uint16_t converted_temp;
    uint16_t converted_humidity;


} sensorReadings;

//
// Function Prototypes
//
bool sensors_openAirCalibration(sensorReadings *sensorData); //records the openAir calibration values
bool sensors_getData(sensorReadings *sensorData); //get sensor data
bool sensors_convertData(sensorReadings *sensorData); //convert sensor data

//////////////////////////////////////////////////////////////////////////////////////////////
//                                                                                      //////
//                                      sensors_logData                                 //////
//                                                                                      //////
//! @param sensorData : struct that holds sensor values                                  //////
//! @param logData : 1 to log for algorithm, 0 to print adc values                       //////
//! @param sample : 'B' if its jsut box, 'N' if its a banana, 'T' if its a tomatoes      //////
//! @param eggStatus : 'E' if theres an egg, 'X' if NA                                   //////
//! @param larvaeStatus : 'L' if theres larvae, 'X' if theres no Larvae                  //////
//! @param pupaeStatus : 'P' if theres pupae, 'X' if theres no pupae                     //////
//! @param adultStatus : 'A' if theres an adult, 'X' if theres no adult                  //////
//! @param sampleAge : int, days the sample has been in the box                          //////
//                                                                                      //////
//////////////////////////////////////////////////////////////////////////////////////////////
bool sensors_logData(sensorReadings *sensorData, bool logData, char sample, char eggStatus, char larvaeStatus, char pupaeStatus, char adultStatus, int sampleAge); //log the data


/// BME280 Prototypes


#endif

