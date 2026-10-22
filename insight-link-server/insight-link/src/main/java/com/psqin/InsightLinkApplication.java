package com.psqin;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * 
 */
@EnableTransactionManagement
@SpringBootApplication
@Slf4j
public class InsightLinkApplication {
    public static void main(String[] args) {
        SpringApplication.run(InsightLinkApplication.class, args);
    }
}
