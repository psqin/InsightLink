package com.psqin.controller.teacher;

import com.psqin.domain.dto.NoticeDTO;
import com.psqin.domain.entity.SystemNotice;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.NoticeService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.format.annotation.DateTimeFormat;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.LocalDateTime;

/**
 *
 */
@Api(tags = "通知相关接口")
@RestController
@RequestMapping("/teacher/notice")
@Slf4j
public class NoticeController {
    @Autowired
    private NoticeService noticeService;

    @PostMapping
    @ApiOperation("发送通知信息")
    public Result save(@RequestBody NoticeDTO noticeDTO) {
        noticeService.save(noticeDTO);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除通知信息")
    public Result delete(@PathVariable Long id) {
        noticeService.delete(id);
        return Result.success();
    }

    @PutMapping("/{id}")
    @ApiOperation("修改通知信息")
    public Result update(@PathVariable Long id, @RequestBody NoticeDTO noticeDTO) {
        noticeService.update(id, noticeDTO);
        return Result.success();
    }

    @GetMapping("/{id}")
    @ApiOperation("查询通知详情")
    public Result<SystemNotice> getById(@PathVariable Long id) {
        return Result.success(noticeService.getById(id));
    }

    @GetMapping("/mine")
    @ApiOperation("查询我发布的通知列表（分页+模糊）")
    public Result<PageResult> listMy(
            @RequestParam(required = false) String title,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate beginDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer pageSize
    ) {
        LocalDateTime beginTime = beginDate != null ? beginDate.atStartOfDay() : null;
        LocalDateTime endTime = endDate != null ? endDate.atTime(LocalTime.of(23,59,59)) : null;
        PageResult pr = noticeService.pageQueryMine(title, beginTime, endTime, page, pageSize);
        return Result.success(pr);
    }
}
