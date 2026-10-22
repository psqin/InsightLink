package com.psqin.controller.admin;

import com.psqin.mapper.*;
import com.psqin.result.Result;
import com.psqin.service.ReportService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.LinkedHashMap;
import java.util.Map;

@Api(tags = "管理员-报表数据接口")
@RestController("AdminReportController")
@RequestMapping("/admin/report")
@Slf4j
public class ReportController {

    @Autowired
    private ReportService reportService;

    @GetMapping("/overview")
    @ApiOperation("概览数据")
    public Result<Map<String, Object>> overview() {
        return Result.success(reportService.overview());
    }

    @GetMapping("/trend")
    @ApiOperation("近N日趋势数据")
    public Result<Map<String, Object>> trend(Integer days) {
        return Result.success(reportService.trend(days));
    }

    @GetMapping("/distribution/school")
    @ApiOperation("学校维度分布")
    public Result<Map<String, Object>> distributionSchool() {
        return Result.success(reportService.distributionSchool());
    }
}
