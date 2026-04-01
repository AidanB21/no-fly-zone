/// Created Su 2/22/26 @ 12pm  by Kailash Pillai

/// Simple reads sensor data from the MCU and stuff

#include "sensorReader.h"



bool sensors_openAirCalibration(sensorReadings *sensorData){

            /// To loop and average NADC Values ///
    const uint16_t N = 50;
    uint32_t sum_MQ3 = 0, sum_MQ135 = 0, sum_MQ131 = 0;
    uint32_t sum_MQ138 = 0, sum_TGS2602 = 0;
    int i;

    for(i = 0; i < N; i++) {
                    //////////////////////////////////
                    //// ADCA  - MQ3, MQ135, MQ131 ///  
                    //////////////////////////////////

        // Convert, wait for completion, and store results
        ADC_forceMultipleSOC(ADCA_BASE, (ADC_FORCE_SOC0 | ADC_FORCE_SOC1 | ADC_FORCE_SOC2));

        // Wait for ADCA to complete, then acknowledge flag
        while(ADC_getInterruptStatus(ADCA_BASE, ADC_INT_NUMBER1) == false)
        {
        }       
        ADC_clearInterruptStatus(ADCA_BASE, ADC_INT_NUMBER1);

                    //////////////////////////////////
                    //// ADCB  - MQ138, TGS2602    ///  
                    //////////////////////////////////

        // Convert, wait for completion, and store results
        ADC_forceMultipleSOC(ADCB_BASE, (ADC_FORCE_SOC0 | ADC_FORCE_SOC1));

        // Wait for ADCA to complete, then acknowledge flag
        while(ADC_getInterruptStatus(ADCB_BASE, ADC_INT_NUMBER1) == false)
        {
        }       
        ADC_clearInterruptStatus(ADCB_BASE, ADC_INT_NUMBER1);

                // accumulate results
        sum_MQ3     += ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER0);
        sum_MQ135   += ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER1);
        sum_MQ131   += ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER2);
        sum_MQ138   += ADC_readResult(ADCBRESULT_BASE, ADC_SOC_NUMBER0);
        sum_TGS2602 += ADC_readResult(ADCBRESULT_BASE, ADC_SOC_NUMBER1);

    }


    // store averages into struct members
    sensorData->raw_MQ3     = (uint16_t)(sum_MQ3     / N);
    sensorData->raw_MQ135   = (uint16_t)(sum_MQ135   / N);
    sensorData->raw_MQ131   = (uint16_t)(sum_MQ131   / N);
    sensorData->raw_MQ138   = (uint16_t)(sum_MQ138   / N);
    sensorData->raw_TGS2602 = (uint16_t)(sum_TGS2602 / N);

        // store averages into struct members
    sensorData->raw_MQ3     = (uint16_t)(sum_MQ3     / N);
    sensorData->raw_MQ135   = (uint16_t)(sum_MQ135   / N);
    sensorData->raw_MQ131   = (uint16_t)(sum_MQ131   / N);
    sensorData->raw_MQ138   = (uint16_t)(sum_MQ138   / N);
    sensorData->raw_TGS2602 = (uint16_t)(sum_TGS2602 / N);


            /// Now log the data ///
    char mlLogBuffer[255];
    int logLength = sprintf(mlLogBuffer, "%u,%u,%u,%u,%u\r\n", sensorData->raw_MQ3, sensorData->raw_MQ135, sensorData->raw_MQ138, sensorData->raw_MQ131, sensorData->raw_TGS2602);
    SCI_writeCharArray(SCIA_BASE, (const uint16_t *) mlLogBuffer, (uint16_t)logLength);

    DEVICE_DELAY_US(1000000 * 2); //delays for 5 seconds



}


//*****************************************************************************
//
//! Sets up the MCU to read sensor data from the ADC and temp/humidity module sotres in raw members
//!
//! \param sensorData is struct passed by reference
//!
//! \return bool True if everyhting is read, False if it messes up somewhere I guess
//*****************************************************************************


bool sensors_getData(sensorReadings *sensorData){

            /// To loop and average NADC Values ///
    const uint16_t N = 50;
    uint32_t sum_MQ3 = 0, sum_MQ135 = 0, sum_MQ131 = 0;
    uint32_t sum_MQ138 = 0, sum_TGS2602 = 0;
    int i;

    for(i = 0; i < N; i++) {
                    //////////////////////////////////
                    //// ADCA  - MQ3, MQ135, MQ131 ///  
                    //////////////////////////////////

        // Convert, wait for completion, and store results
        ADC_forceMultipleSOC(ADCA_BASE, (ADC_FORCE_SOC0 | ADC_FORCE_SOC1 | ADC_FORCE_SOC2));

        // Wait for ADCA to complete, then acknowledge flag
        while(ADC_getInterruptStatus(ADCA_BASE, ADC_INT_NUMBER1) == false)
        {
        }       
        ADC_clearInterruptStatus(ADCA_BASE, ADC_INT_NUMBER1);

                    //////////////////////////////////
                    //// ADCB  - MQ138, TGS2602    ///  
                    //////////////////////////////////

        // Convert, wait for completion, and store results
        ADC_forceMultipleSOC(ADCB_BASE, (ADC_FORCE_SOC0 | ADC_FORCE_SOC1));

        // Wait for ADCA to complete, then acknowledge flag
        while(ADC_getInterruptStatus(ADCB_BASE, ADC_INT_NUMBER1) == false)
        {
        }       
        ADC_clearInterruptStatus(ADCB_BASE, ADC_INT_NUMBER1);

                // accumulate results
        sum_MQ3     += ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER0);
        sum_MQ135   += ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER1);
        sum_MQ131   += ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER2);
        sum_MQ138   += ADC_readResult(ADCBRESULT_BASE, ADC_SOC_NUMBER0);
        sum_TGS2602 += ADC_readResult(ADCBRESULT_BASE, ADC_SOC_NUMBER1);

    }


    // store averages into struct members
    sensorData->raw_MQ3     = (uint16_t)(sum_MQ3     / N);
    sensorData->raw_MQ135   = (uint16_t)(sum_MQ135   / N);
    sensorData->raw_MQ131   = (uint16_t)(sum_MQ131   / N);
    sensorData->raw_MQ138   = (uint16_t)(sum_MQ138   / N);
    sensorData->raw_TGS2602 = (uint16_t)(sum_TGS2602 / N);

    return true; //just returns true for now I guess
}


//*****************************************************************************
//
//! Converts the sensor data and stores in converted members
//!
//! \param sensorData is the struct passed by reference
//!
//! \return bool True if everyhting is read, False if it messes up somewhere I guess
//*****************************************************************************
bool sensors_convertData(sensorReadings *sensorData){

                /// For now its not converting anything just having raw adc values

        /// Store Sensor Data Into Struct Members ///
/*
    sensorData->converted_MQ3 = ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER0); //25.0f + ((float) sensorData->raw_MQ3) * (500.0f - 25.0f) / (4095.0f);
    sensorData->converted_MQ135 = ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER1); //10.0f + ((float) sensorData->raw_MQ135) * (1000.0f - 10.0f) / (4095.0f);
    sensorData->converted_MQ131 = ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER2); //10.0f + ((float) sensorData->raw_MQ131) * (1000.0f - 10.0f) / (4095.0f);
    sensorData->converted_MQ138 =  ADC_readResult(ADCBRESULT_BASE, ADC_SOC_NUMBER0); //5.0f + ((float) sensorData->raw_MQ138) * (500.0f - 5.0f) / (4095.0f);
    sensorData->converted_TGS2602 =  ADC_readResult(ADCBRESULT_BASE, ADC_SOC_NUMBER1); //1.0f + ((float) sensorData->raw_TGS2602) * (30.0f - 1.0f) / (4095.0f);
*/

    sensorData->converted_MQ3 = sensorData->raw_MQ3;
    sensorData->converted_MQ135 = sensorData->raw_MQ135;
    sensorData->converted_MQ131 = sensorData->raw_MQ131;
    sensorData->converted_MQ138 =  sensorData->raw_MQ138;
    sensorData->converted_TGS2602 =  sensorData->raw_TGS2602;

    return true;
}


//////////////////////////////////////////////////////////////////////////////////////////////
//                                                                                      //////
//!                                      sensors_logData                                 //////
//                                                                                      //////
//! @param sensorData : struct that holds sensor values                                  //////
//! @param logData : 1 to log for algorithm, 0 to print adc values                       //////
//! @param sample : 'B' if its jsut box, 'B' if its a banana, 'T' if its a tomatoes      //////
//! @param eggStatus : 'E' if theres an egg, 'X' if NA                                   //////
//! @param larvaeStatus : 'L' if theres larvae, 'X' if theres no Larvae                  //////
//! @param pupaeStatus : 'P' if theres pupae, 'X' if theres no pupae                     //////
//! @param adultStatus : 'A' if theres an adult, 'X' if theres no adult                  //////
//! @param sampleAge : int, days the sample has been in the box                          //////
//                                                                                      //////
//////////////////////////////////////////////////////////////////////////////////////////////
bool sensors_logData(sensorReadings *sensorData, bool logData, char sample, char eggStatus, char larvaeStatus, char pupaeStatus, char adultStatus, int sampleAge){
    
/*
    sensorData->converted_MQ3 = (uint16_t) (sensorData->converted_MQ3 + 0.5f);
    sensorData->converted_MQ135 = (uint16_t) (sensorData->converted_MQ135 + 0.5f);
    sensorData->converted_MQ131 = (uint16_t) (sensorData->converted_MQ131 + 0.5f);
    sensorData->converted_MQ138 = (uint16_t) (sensorData->converted_MQ138 + 0.5f);
    sensorData->converted_TGS2602 = (uint16_t) (sensorData->converted_TGS2602 + 0.5f);
*/


    if (!logData) { //if we are not logging data

         char logBuffer[255];

        //int logLength = sprintf(logBuffer, "MQ3:%uppm, MQ135:%uppm, MQ138:%uppm, MQ131:%uppm, TGS2602:%uppm, Temp:%uF, Humidity:%u\r\n", sensorData->converted_MQ3, sensorData->converted_MQ135, sensorData->converted_MQ138, sensorData->converted_MQ131, sensorData->converted_TGS2602, sensorData->converted_temp, sensorData->converted_humidity);
        int logLength = sprintf(logBuffer, "MQ3:%u, MQ135:%u, MQ138:%u, MQ131:%u, TGS2602:%u\r\n", sensorData->converted_MQ3, sensorData->converted_MQ135, sensorData->converted_MQ138, sensorData->converted_MQ131, sensorData->converted_TGS2602);

        SCI_writeCharArray(SCIA_BASE, (const uint16_t *) logBuffer, (uint16_t)logLength);

    } else { //now we are logging the data
        char mlLogBuffer[255];
        int logLength = sprintf(mlLogBuffer, "%u,%u,%u,%u,%u,%c,%c,%c,%c,%c,%d\r\n", sensorData->converted_MQ3, sensorData->converted_MQ135, sensorData->converted_MQ138, sensorData->converted_MQ131, sensorData->converted_TGS2602, sample, eggStatus, larvaeStatus, pupaeStatus, adultStatus, sampleAge);
        SCI_writeCharArray(SCIA_BASE, (const uint16_t *) mlLogBuffer, (uint16_t)logLength);
    }

    return true;
}

/// Sample I2C write operation. 
bool I2C_writeBytes(uint32_t base, uint16_t targetAddr, const uint8_t *data, uint16_t len) {
    uint32_t timeout;

    // Wait if a previous STOP is still in progress

    while(I2C_getStopConditionStatus(base) && --timeout);
    if(timeout == 0U) return false;

    // Wait while bus busy
    timeout = I2C_TIMEOUT;
    while(I2C_isBusBusy(base) && --timeout);
    if(timeout == 0U) return false;

    // Set target address and data count
    I2C_setTargetAddress(base, targetAddr);
    I2C_setDataCount(base, len);

    // Controller‑transmitter mode, no repeat
    I2C_setConfig(base, I2C_CONTROLLER_SEND_MODE);

    // Load TX bytes
    int i;
    for(i = 0; i < len; i++)
    {
        I2C_putData(base, data[i]);
    }

    // Generate START + (implicit) STOP when count hits 0
    I2C_sendStartCondition(base);
    I2C_sendStopCondition(base);

    // Wait for STOP complete
    timeout = I2C_TIMEOUT;
    while(!I2C_getStopConditionStatus(base) && --timeout);
    if(timeout == 0U) return false;

    return true;
}

/// Sampel I2C read register thing
bool I2C_readRegister(uint32_t base, uint16_t targetAddr, uint8_t reg, uint8_t *data, uint16_t len) {
    uint32_t timeout;

    // ---------- Phase 1: write register address ----------
    timeout = I2C_TIMEOUT;
    while(I2C_getStopConditionStatus(base) && --timeout);
    if(timeout == 0U) return false;

    timeout = I2C_TIMEOUT;
    while(I2C_isBusBusy(base) && --timeout);
    if(timeout == 0U) return false;

    I2C_setTargetAddress(base, targetAddr);
    I2C_setDataCount(base, 1);
    I2C_setConfig(base, I2C_CONTROLLER_SEND_MODE);

    I2C_putData(base, reg);

    // START, no STOP (we’ll issue a repeated‑start)
    I2C_sendStartCondition(base);

    // Wait until the register byte is shifted out
    timeout = I2C_TIMEOUT;
    while(!(I2C_getStatus(base) & I2C_STS_REG_ACCESS_RDY) && --timeout);
    if(timeout == 0U) return false;
    I2C_clearStatus(base, I2C_STS_REG_ACCESS_RDY);

    // ---------- Phase 2: repeated‑start read ----------
    I2C_setDataCount(base, len);
    I2C_setConfig(base, I2C_CONTROLLER_RECEIVE_MODE);

    // Repeated START
    I2C_sendStartCondition(base);
    int i;
    // For the last byte we need to send NACK then STOP
    for(i = 0; i < len; i++)
    {
        // wait until data is ready
        timeout = I2C_TIMEOUT;
        while(!(I2C_getStatus(base) & I2C_STS_RX_DATA_RDY) && --timeout);
        if(timeout == 0U) return false;

        if(i == (len - 1U))
        {
            // prepare NACK+STOP before reading final byte
            I2C_sendNACK(base);
            I2C_sendStopCondition(base);
        }

        data[i] = (uint8_t)I2C_getData(base);
        I2C_clearStatus(base, I2C_STS_RX_DATA_RDY);
    }

    // Wait for STOP to finish
    timeout = I2C_TIMEOUT;
    while(!I2C_getStopConditionStatus(base) && --timeout);
    if(timeout == 0U) return false;

    return true;
}




