#!/bin/bash

file_name="test_suite_library.bash"

function echo2_and_issue {
  test_log=$1
  cmd_str=$2  
  echo "  > $cmd_str"|tee -a $test_log
  mce_ret=`$cmd_str`
}

function echo2 {
  test_log=$1
  str=$2
  echo "$str"|tee -a $test_log
#  echo "$str">>$test_log
#  echo "$str"  
}

function test_result_analysis {
  tester_notes="fail"

  # Append/ output test information
  echo2 $tlog "$test_type_str"  
  
  if [[ $test_type_str == No* ]]; then
    # The test does not exist, therefore results are not checked
    echo2 $tlog ""  
  else
    # Parse the tester's input.  Input must begin with "pass" or "fail".
    while [ 1 ]; do
      
# embed the interactive mode check after each test type      
      # If we are not in deaf mode, then wait for the reponse
      if [ $interactive_mode -eq 0 ]; then

        if [ $autotest_type -eq 0 -o $autotest_type -eq 2 ]; then
          # One value within a certain range
          echo2 $tlog "Pass criterion: between $autotest_lb and $autotest_ub"          
        elif [ $autotest_type -eq 1 ]; then
          # Text
          echo2 $tlog "Pass criterion: contains $autotest_text"          
        elif [ $autotest_type -eq 3 ]; then
          # Does file exist
          echo2 $tlog "Pass criterion: does file exist"          
        elif [ $autotest_type -eq 4 ]; then
          # Does a single value occur between two distinct ranges?
          echo2 $tlog "Pass criterion: is the value between $autotest_lb - $autotest_lub or $autotest_ulb - $autotest_ub"
        else
          # skip check here
          :
        fi
        
        echo "Does the test [pass] or [fail]?  Type 'pass'/'fail' + comments, and press [ENTER]"
        read tester_notes

      else
      
        if [ $autotest_type -eq 0 ]; then
          # One value within a certain range
          if [ $mce_ret -ge $autotest_lb -a $mce_ret -le $autotest_ub ]; then
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
        elif [ $autotest_type -eq 1 ]; then
          # Text
          substring=${mce_ret:1:2}
          if [ $substring = $autotest_text ]; then
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
        elif [ $autotest_type -eq 2 ]; then
          # do multiple value checking here
#          substring=${mce_ret:0:1}
#          if [ mce_ret[0] -ge $autotest_lb ]; then
#            tester_notes="pass"
#          else
            tester_notes="fail"
#          fi
        elif [ $autotest_type -eq 3 ]; then
          if [ -s $data_path_file_name ]; then
            # does file exist?
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
	elif [ $autotest_type -eq 4 ]; then
          if [ $mce_ret -ge $autotest_lb -a $mce_ret -le $autotest_lub ]; then
            tester_notes="pass"
          elif [ $mce_ret -ge $autotest_ulb -a $mce_ret -le $autotest_ub ]; then
            tester_notes="pass"
          else
            tester_notes="fail"
          fi
        else
          # skip check here
          tester_notes="fail"
        fi
      fi
      
      if [[ $tester_notes == pass* ]]; then
        test_passes=$(($test_passes + 1))
        # Append the tester's ID and notes to the test log

        if [ $interactive_mode -eq 0 ]; then
          echo "$file_name : test $test_num : $tester_id : $tester_notes">>$tlog
        else
          echo2 $tlog "$file_name : test $test_num : auto : $tester_notes"
        fi        
        echo2 $tlog ""
        break
      elif [[ $tester_notes == fail* ]]; then
        test_failures=$(($test_failures + 1)) 
        # Append the tester's ID and notes to the test log
        if [ $interactive_mode -eq 0 ]; then
          echo "$file_name : test $test_num : $tester_id : $tester_notes">>$tlog
        else
          echo2 $tlog "$file_name : test $test_num : auto : $tester_notes"
        fi
        echo2 $tlog ""
        break
      elif [[ $tester_notes == none* ]]; then
        break
      fi
    done
  fi
}
