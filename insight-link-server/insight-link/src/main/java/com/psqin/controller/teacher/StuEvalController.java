package com.psqin.controller.teacher;

import com.psqin.domain.dto.StuEvalDTO;
import com.psqin.domain.dto.StuMatTeaSearchPageDTO;
import com.psqin.domain.vo.StudentMaterialVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.StuEvalService;
import com.psqin.service.StuMaterialService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Api(tags = "评价相关接口")
@RestController
@RequestMapping("/teacher/evaluation")
@Slf4j
public class StuEvalController {

    @Autowired
    private StuEvalService stuEvalService;

    @Autowired
    private StuMaterialService stuMaterialService;

    @PostMapping
    @ApiOperation("材料评价")
    public Result save(@RequestBody StuEvalDTO stuEvalDTO) {
        log.info("给予评价：{}", stuEvalDTO);
        stuEvalService.save(stuEvalDTO);
        return Result.success();
    }

    @DeleteMapping
    @ApiOperation("删除评价")
    public Result delete(Long id) {
        log.info("删除评价：{}", id);
        stuEvalService.delete(id);
        return Result.success();
    }

    @PutMapping
    @ApiOperation("修改评价")
    public Result update(@RequestBody StuEvalDTO stuEvalDTO) {
        log.info("修改评价：{}", stuEvalDTO);
        stuEvalService.update(stuEvalDTO);
        return Result.success();
    }

    @GetMapping("/{id}")
    @ApiOperation("查看材料和评价")
    public Result<StudentMaterialVO> getById(@PathVariable Long id) {
        log.info("查看材料和评价：{}", id);
        StudentMaterialVO materialVO = stuMaterialService.getById(id);
        return Result.success(materialVO);
    }

    @GetMapping("/page")
    @ApiOperation("分页+模糊查询材料列表（仅导师绑定学生）")
    public Result<PageResult> page(StuMatTeaSearchPageDTO dto) {
        log.info("分页查询学生材料列表：{}", dto);
        PageResult pageResult = stuEvalService.pageQueryMaterials(dto);
        return Result.success(pageResult);
    }
}
