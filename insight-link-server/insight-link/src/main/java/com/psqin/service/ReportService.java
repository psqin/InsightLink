package com.psqin.service;

import java.util.Map;

public interface ReportService {
    Map<String, Object> overview();
    Map<String, Object> trend(Integer days);
    Map<String, Object> distributionSchool();
}
