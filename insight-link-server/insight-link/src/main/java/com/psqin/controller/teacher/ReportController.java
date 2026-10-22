package com.psqin.controller.teacher;

import com.psqin.result.Result;
import com.psqin.service.TeacherReportService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@Api(tags = "导师-报表数据接口")
@RestController("TeacherReportController")
@RequestMapping("/teacher/report")
@Slf4j
public class ReportController {

    @Autowired
    private TeacherReportService teacherReportService;

    @GetMapping("/overview")
    @ApiOperation("概览数据")
    public Result<Map<String, Object>> overview() {
        return Result.success(teacherReportService.overview());
    }

    @GetMapping("/trend")
    @ApiOperation("评价次数趋势(折线图)")
    public Result<Map<String, Object>> trend(Integer days) {
        return Result.success(teacherReportService.evalTrend(days));
    }
}
