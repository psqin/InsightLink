package com.psqin.service;

import java.util.Map;

public interface TeacherReportService {
    Map<String, Object> overview();
    Map<String, Object> evalTrend(Integer days);
}
