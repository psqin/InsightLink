package com.psqin.controller;

import com.psqin.domain.entity.SysDept;
import com.psqin.domain.entity.Universities;
import com.psqin.result.Result;
import com.psqin.mapper.SysDeptMapper;
import com.psqin.service.SysDeptService;
import com.psqin.service.UniversityService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 学校 - 院系 - 专业 - 班级
 */
@Api(tags = "学校院系专业班级相关接口")
@RestController
@RequestMapping("/school-hierarchy")
@Slf4j
public class SchoolHierarchyController {

    @Autowired
    private UniversityService universityService;
    @Autowired
    private SysDeptService sysDeptService;

    // ===================== 学校相关接口 =====================
    /**
     * 模糊查询学校
     */
    @GetMapping("/universities/search")
    public Result searchUniversitiesByName(@RequestParam String name) {
        log.info("学校模糊查询: {}", name);
        return Result.success(universityService.query(name));
    }
    // ===================== 院系 / 专业 / 班级 =====================
    @GetMapping("/universities/{universityId}/colleges")
    @ApiOperation("根据学校ID查询院系列表")
    public Result<List<SysDept>> listColleges(@PathVariable Long universityId) {
        log.info("根据学校ID查询院系: {}", universityId);
        return Result.success(sysDeptService.listCollegesByUniversityId(universityId));
    }

    @GetMapping("/colleges/{collegeId}/majors")
    @ApiOperation("根据院系ID查询专业列表")
    public Result<List<SysDept>> listMajors(@PathVariable Long collegeId) {
        log.info("根据院系ID查询专业: {}", collegeId);
        return Result.success(sysDeptService.listMajorsByCollegeId(collegeId));
    }

    @GetMapping("/majors/{majorId}/classes")
    @ApiOperation("根据专业ID查询班级列表")
    public Result<List<SysDept>> listClasses(@PathVariable Long majorId) {
        log.info("根据专业ID查询班级: {}", majorId);
        return Result.success(sysDeptService.listClassesByMajorId(majorId));
    }

}
